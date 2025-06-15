import pandas as pd
from .inventory_manager import find_product_matches

def process_and_validate_order(extracted_order: dict, inventory_df: pd.DataFrame):
    """
    Processes the extracted order, validates each product against the inventory,
    and checks for issues like MOQ and ambiguity.

    Returns:
        A dictionary containing the fully processed and validated order data.
    """
    if not extracted_order or 'products' not in extracted_order:
        return {"error": "Invalid extracted order data."}

    processed_items = []
    order_issues = []

    for item in extracted_order.get("products", []):
        req_name = item.get("product_name")
        req_qty = item.get("quantity")

        if not req_name or not req_qty:
            order_issues.append(f"Invalid item in request, missing name or quantity: {item}")
            continue

        matches = find_product_matches(req_name, inventory_df)

        if not matches:
            processed_items.append({
                "requested_name": req_name,
                "requested_quantity": req_qty,
                "status": "NOT_FOUND",
                "issue": f"No product found matching '{req_name}'.",
                "matched_sku": None
            })
        elif len(matches) > 1:
            possible_skus = [m['SKU'] for m in matches]
            processed_items.append({
                "requested_name": req_name,
                "requested_quantity": req_qty,
                "status": "MULTIPLE_MATCHES_FOUND",
                "issue": f"Request '{req_name}' is ambiguous. Possible SKUs: {possible_skus}",
                "matched_sku": None,
                "potential_matches": matches
            })
        else: # Exactly one match found
            product = matches[0]
            moq = product['MinOrderQty']
            
            if req_qty < moq:
                processed_items.append({
                    "requested_name": req_name,
                    "requested_quantity": req_qty,
                    "status": "MOQ_NOT_MET",
                    "issue": f"Quantity {req_qty} is below the Minimum Order Quantity of {moq}.",
                    "matched_sku": product['SKU'],
                    "product_details": product
                })
            else:
                # This item is fully validated!
                processed_items.append({
                    "requested_name": req_name,
                    "requested_quantity": req_qty,
                    "status": "VALIDATED",
                    "issue": None,
                    "matched_sku": product['SKU'],
                    "product_details": product
                })

    # Assemble the final processed order object
    final_order = {
        "customer_name": extracted_order.get("customer_name"),
        "delivery_address": extracted_order.get("delivery_address"),
        "delivery_date": extracted_order.get("delivery_date"),
        "customer_notes": extracted_order.get("customer_notes"),
        "processed_line_items": processed_items,
    }
    
    return final_order
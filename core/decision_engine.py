import pandas as pd
from .inventory_manager import find_product_matches

def process_and_validate_order(extracted_order: dict, inventory_df: pd.DataFrame):
    """
    Processes the extracted order, validates each product against the inventory,
    and checks for issues like MOQ and ambiguity.
    """
    if not extracted_order:
        return {"error": "Received empty or invalid extracted order data."}

    # Initialize the final structure
    final_order = {
        "customer_name": extracted_order.get("customer_name"),
        "delivery_address": extracted_order.get("delivery_address"),
        "delivery_date": extracted_order.get("delivery_date"),
        "customer_notes": extracted_order.get("customer_notes"),
        "processed_line_items": [],
    }

    product_list_from_ai = extracted_order.get("products", [])
    
    for item in product_list_from_ai:
        req_name = item.get("product_name")
        req_qty = int(item.get("quantity", 0))

        if not req_name or req_qty <= 0:
            continue

        matches = find_product_matches(req_name, inventory_df)

        if not matches:
            final_order["processed_line_items"].append({
                "requested_name": req_name, "requested_quantity": req_qty,
                "status": "NOT_FOUND",
                "issue": f"No product found matching '{req_name}'.",
                "matched_sku": None
            })
        elif len(matches) > 1:
            possible_skus = [m['SKU'] for m in matches]
            final_order["processed_line_items"].append({
                "requested_name": req_name, "requested_quantity": req_qty,
                "status": "MULTIPLE_MATCHES_FOUND",
                "issue": f"Request '{req_name}' is ambiguous. Possible SKUs: {possible_skus}",
                "matched_sku": None,
                "potential_matches": [m['SKU'] for m in matches]
            })
        else: # Exactly one match
            product = matches[0]
            # Safely convert to numeric, handling potential None values
            moq = pd.to_numeric(product.get('MinOrderQty'), errors='coerce')
            
            if moq is not None and req_qty < moq:
                final_order["processed_line_items"].append({
                    "requested_name": req_name, "requested_quantity": req_qty,
                    "status": "MOQ_NOT_MET",
                    "issue": f"Quantity {req_qty} is below the Minimum Order Quantity of {moq}.",
                    "matched_sku": product['SKU'],
                    "product_details": { "SKU": product["SKU"], "Price": product.get("Price") }
                })
            else: # Validated!
                final_order["processed_line_items"].append({
                    "requested_name": req_name, "requested_quantity": req_qty,
                    "status": "VALIDATED",
                    "issue": None,
                    "matched_sku": product['SKU'],
                    "product_details": { "SKU": product["SKU"], "Price": product.get("Price"), "Name": product["ProductName"] }
                })
    
    return final_order
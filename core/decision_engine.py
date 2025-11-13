from .inventory_manager import find_product_matches
import pandas as pd

def process_and_validate_order(extracted_order: dict, inventory_df: pd.DataFrame):
    """
    Processes the extracted order, validating against MOQ, ambiguity, and stock levels.
    """
    if not extracted_order:
        return {"error": "Received empty or invalid extracted order data."}

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
        
        sku_key = 'Product_Code'
        moq_key = 'Min_Order_Quantity'
        stock_key = 'Available_in_Stock'
        name_key = 'Product_Name'
        price_key = 'Price'

        if not matches:
            final_order["processed_line_items"].append({
                "requested_name": req_name, "requested_quantity": req_qty,
                "status": "NOT_FOUND",
                "issue": f"No product found matching '{req_name}'.",
            })
        elif len(matches) > 1:
            final_order["processed_line_items"].append({
                "requested_name": req_name, "requested_quantity": req_qty,
                "status": "MULTIPLE_MATCHES_FOUND",
                "issue": f"Request '{req_name}' is ambiguous. Possible SKUs: {[m[sku_key] for m in matches]}",
            })
        else:
            product = matches[0]
            moq = pd.to_numeric(product.get(moq_key), errors='coerce')
            stock = pd.to_numeric(product.get(stock_key), errors='coerce')

            if moq is not None and req_qty < moq:
                final_order["processed_line_items"].append({
                    "requested_name": req_name, "requested_quantity": req_qty,
                    "status": "MOQ_NOT_MET",
                    "issue": f"Quantity {req_qty} is below the Minimum Order Quantity of {moq}.",
                    "product_details": product
                })
            elif stock is not None and stock < req_qty: # Check if stock is sufficient
                final_order["processed_line_items"].append({
                    "requested_name": req_name, "requested_quantity": req_qty,
                    "status": "INSUFFICIENT_STOCK",
                    "issue": f"Requested quantity {req_qty} exceeds available stock of {int(stock)} for '{product[name_key]}'.",
                    "product_details": product
                })
            else: # All checks pass, it's a validated item!
                # --- THIS IS THE FIX ---
                # We need to create the full dictionary structure here.
                final_order["processed_line_items"].append({
                    "requested_name": req_name,
                    "requested_quantity": req_qty, # Added this back
                    "status": "VALIDATED",
                    "issue": None,
                    "product_details": product # The full product dict is needed
                })
                # --- END OF FIX ---
    
    return final_order
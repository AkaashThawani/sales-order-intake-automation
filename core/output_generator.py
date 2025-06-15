import json
import re
from datetime import datetime
import os
import pandas as pd # <-- Import pandas here

def create_sales_order_json(processed_order: dict, output_folder="output"):
    """
    Takes the fully processed order data and generates a structured JSON file.
    This version safely handles NaN values from pandas.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    customer_name = processed_order.get("customer_name", "UnknownCustomer")
    safe_customer_name = re.sub(r'[^a-zA-Z0-9_-]', '', str(customer_name).replace(' ', '-'))
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"SO_{safe_customer_name}_{timestamp}.json"
    filepath = os.path.join(output_folder, filename)

    # Final JSON structure
    output_data = {
        "sales_order_summary": {
            "customer_name": processed_order.get("customer_name"),
            "delivery_address": processed_order.get("delivery_address"),
            "requested_delivery_date": processed_order.get("delivery_date"),
            "notes": processed_order.get("customer_notes"),
            "generation_timestamp_utc": datetime.utcnow().isoformat()
        },
        "consolidation_suggestions": processed_order.get("consolidation_suggestions", []),
        "line_items": [],
        "issues_for_review": []
    }

    for item in processed_order.get("processed_line_items", []):
        if item["status"] == "VALIDATED":
            product = item["product_details"]
            
            # --- THIS IS THE FIX ---
            # Safely get quantity and price, and check for NaN values.
            quantity = item.get("requested_quantity", 0)
            unit_price = product.get("Price")
            total_price = None

            # Check if unit_price is NaN, and if so, convert it to None for JSON compatibility.
            if pd.isna(unit_price):
                unit_price = None

            # Only calculate total_price if unit_price is a valid number.
            if isinstance(unit_price, (int, float)):
                total_price = round(quantity * unit_price, 2)
            # --- END OF FIX ---

            output_data["line_items"].append({
                "sku": product.get("SKU"),
                "product_name": product.get("Name"),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price
            })
        else: # Any other status is an issue
            output_data["issues_for_review"].append({
                "requested_item": item.get("requested_name"),
                "status": item.get("status"),
                "details": item.get("issue")
            })
            
    try:
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"\n✅ Successfully created sales order file: {filepath}")
        return filepath
    except Exception as e:
        print(f"\n❌ Error creating JSON file: {e}")
        return None
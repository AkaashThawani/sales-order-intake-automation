import json
import re
from datetime import datetime
import os
import pandas as pd

def create_sales_order_json(processed_order: dict, output_folder="output"):
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    customer_name = processed_order.get("customer_name", "UnknownCustomer")
    safe_customer_name = re.sub(r'[^a-zA-Z0-9_-]', '', str(customer_name).replace(' ', '-'))
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"SO_{safe_customer_name}_{timestamp}.json"
    filepath = os.path.join(output_folder, filename)

    output_data = {
        "sales_order_summary": processed_order.get("sales_order_summary", processed_order),
        "line_items": [],
        "issues_for_review": []
    }
    
    # Restructure the sales_order_summary to ensure it's clean
    summary = processed_order
    output_data["sales_order_summary"] = {
        "customer_name": summary.get("customer_name"),
        "delivery_address": summary.get("delivery_address"),
        "requested_delivery_date": summary.get("delivery_date"),
        "notes": summary.get("customer_notes"),
        "generation_timestamp_utc": datetime.utcnow().isoformat()
    }


    for item in processed_order.get("processed_line_items", []):
        if item.get("status") == "VALIDATED":
            details = item.get("product_details", {})
            quantity = item.get("requested_quantity", 0)
            unit_price = pd.to_numeric(details.get("Price"), errors='coerce')
            total_price = None

            if pd.notna(unit_price):
                total_price = round(quantity * unit_price, 2)

            output_data["line_items"].append({
                "sku": details.get("Product_Code"),
                "product_name": details.get("Product_Name"),
                "quantity": quantity,
                "unit_price": unit_price if pd.notna(unit_price) else None,
                "total_price": total_price
            })
        else:
            output_data["issues_for_review"].append({
                "requested_item": item.get("requested_name"),
                "status": item.get("status"),
                "details": item.get("issue")
            })
            
    try:
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=4, default=str) # Use default=str to handle any rogue numpy types
        print(f"\n✅ Successfully created sales order file: {filepath}")
        return filepath
    except Exception as e:
        print(f"\n❌ Error creating JSON file: {e}")
        return None
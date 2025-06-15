import json
import re
from datetime import datetime

def create_sales_order_json(processed_order: dict, output_folder="output"):
    """
    Takes the fully processed order data and generates a structured JSON file.
    """
    import os
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Sanitize customer name for the filename
    customer_name = processed_order.get("customer_name", "UnknownCustomer")
    safe_customer_name = re.sub(r'[^a-zA-Z0-9_-]', '', customer_name.replace(' ', '-'))
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"SO_{safe_customer_name}_{timestamp}.json"
    filepath = os.path.join(output_folder, filename)

    # Structure the final JSON
    output_data = {
        "sales_order_summary": {
            "customer_name": processed_order.get("customer_name"),
            "delivery_address": processed_order.get("delivery_address"),
            "requested_delivery_date": processed_order.get("delivery_date"),
            "notes": processed_order.get("customer_notes"),
            "generation_timestamp_utc": datetime.utcnow().isoformat()
        },
        "line_items": [],
        "issues_for_review": []
    }

    for item in processed_order.get("processed_line_items", []):
        if item["status"] == "VALIDATED":
            product = item["product_details"]
            output_data["line_items"].append({
                "sku": product["SKU"],
                "product_name": product["ProductName"],
                "quantity": item["requested_quantity"],
                "unit_price": product["Price"],
                "total_price": round(item["requested_quantity"] * product["Price"], 2)
            })
        else:
            # If not validated, add it to the issues list
            output_data["issues_for_review"].append({
                "requested_item": item["requested_name"],
                "status": item["status"],
                "details": item["issue"]
            })
            
    try:
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"\n✅ Successfully created sales order file: {filepath}")
        return filepath
    except Exception as e:
        print(f"\n❌ Error creating JSON file: {e}")
        return None
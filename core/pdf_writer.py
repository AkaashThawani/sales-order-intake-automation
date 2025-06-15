import fitz
import json
import os
import platform
from datetime import datetime
import pandas as pd

# --- THE FINAL, CORRECTED COORDINATE BLUEPRINT FOR THE NEW PDF ---
COORDS = {
    # Aligned with the labels from the new PDF image
    "customer_name": (150, 105),
    "delivery_date": (150, 135),
    "address": (150, 165),
    "table": {
        # Y-coordinate for the first data row, placed below the headers
        "first_row_y": 240, 
        "row_height": 31,
        # X-coordinates for each column, centered within the boxes
        "col_code": 40, 
        "col_name": 120, 
        "col_qty": 245,
        "col_price": 300, 
        "col_total": 465, 
        "col_remarks": 530
    },
    # Y-coordinate for the final total, aligned with its label
    "total_amount": (465, 665) 
}

def get_font_paths():
    """Detects the OS and returns the correct paths for standard fonts."""
    os_name = platform.system()
    if os_name == "Windows":
        return {"regular": "C:/Windows/Fonts/arial.ttf"}
    elif os_name == "Darwin":  # macOS
        return {"regular": "/System/Library/Fonts/Supplemental/Arial.ttf"}
    else: # Assume Linux
        # A common fallback path
        return {"regular": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"}

def fill_sales_order_pdf(json_path: str, template_path: str, output_folder="output"):
    """
    Reads a processed order from a JSON file and fills out the new PDF template.
    """
    try:
        with open(json_path, 'r') as f: order_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: JSON file not found at {json_path}")
        return

    doc = fitz.open(template_path)
    page = doc[0]

    try:
        fonts = get_font_paths()
        page.insert_font(fontname="reg", fontfile=fonts["regular"])
    except Exception as e:
        print(f"❌ FONT ERROR: Could not load system fonts. Please ensure Arial or Liberation Sans is available. Error: {e}")
        return

    # --- 1. Fill Header Info ---
    summary = order_data.get("sales_order_summary", {})
    page.insert_text(COORDS["customer_name"], summary.get("customer_name", "N/A"), fontname="reg", fontsize=10)
    page.insert_text(COORDS["delivery_date"], summary.get("requested_delivery_date", "N/A"), fontname="reg", fontsize=10)
    page.insert_text(COORDS["address"], summary.get("delivery_address", "N/A"), fontname="reg", fontsize=10)
    
    # --- 2. Fill Line Items and Issues into the Table ---
    tbl = COORDS["table"]
    current_y = tbl["first_row_y"]
    total_order_amount = 0

    # Combine validated items and items with issues to list them all on the form
    all_items_to_display = order_data.get("line_items", []) + order_data.get("issues_for_review", [])

    for item in all_items_to_display:
        # Get details whether it's a validated item or an issue
        details = item.get("product_details", {})
        qty = item.get("quantity", item.get("requested_quantity", 0))
        price = pd.to_numeric(details.get("Price"), errors='coerce') if details else None
        total_line = None
        
        sku_to_display = details.get("Product_Code", item.get("sku", ""))
        name_to_display = details.get("Product_Name", item.get("product_name", item.get("requested_item", "")))
        remarks_text = item.get("issue", "") # Use the issue as the remark
        
        if item.get("status") == "VALIDATED" and pd.notna(price):
            total_line = qty * price
            total_order_amount += total_line

        # Insert data into PDF table rows
        page.insert_text((tbl["col_code"], current_y), str(sku_to_display or ""), fontname="reg", fontsize=9)
        page.insert_text((tbl["col_name"], current_y), str(name_to_display or ""), fontname="reg", fontsize=9)
        page.insert_text((tbl["col_qty"], current_y), str(qty or ""), fontname="reg", fontsize=9)
        page.insert_text((tbl["col_price"], current_y), f"{price:.2f}" if pd.notna(price) else "", fontname="reg", fontsize=9)
        page.insert_text((tbl["col_total"], current_y), f"{total_line:.2f}" if total_line is not None else "", fontname="reg", fontsize=9)
        page.insert_text((tbl["col_remarks"], current_y), remarks_text or "", fontname="reg", fontsize=8, color=(1, 0, 0)) # Red text for issues
        
        current_y += tbl["row_height"]

    # --- 3. Write Final Total ---
    page.insert_text(COORDS["total_amount"], f"{total_order_amount:.2f}", fontname="reg", fontsize=10)

    # --- 4. Save the new PDF ---
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    safe_name = str(summary.get("customer_name", "ORDER")).replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = os.path.join(output_folder, f"FILLED_SO_{safe_name}_{ts}.pdf")
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    print(f"📄 Successfully created filled PDF: {output_path}")
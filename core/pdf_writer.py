import fitz  # PyMuPDF
import json
import os
from datetime import datetime

# --- This is our coordinate blueprint ---
COORDS = {
    "customer_name": (200, 145),
    "customer_address": (200, 170),
    "delivery_date": (200, 195),
    "table": {
        "first_row_y": 268, "row_height": 23,
        "col_sku": 80, "col_prod": 180, "col_qty": 410, "col_price": 470
    },
    "notes_start_y": 625,
    "issues_start_y": 685
}

def fill_sales_order_pdf(json_path: str, template_path: str, output_folder="output"):
    """
    Reads a processed order from a JSON file and fills out a PDF template
    that already has a pre-drawn table.
    """
    try:
        with open(json_path, 'r') as f:
            order_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: JSON file not found at {json_path}")
        return

    doc = fitz.open(template_path)
    page = doc[0] # Work on the first page

    # --- 1. Fill Header Info ---
    summary = order_data.get("sales_order_summary", {})
    page.insert_text(COORDS["customer_name"], summary.get("customer_name", "N/A"), fontname="helv", fontsize=11)
    page.insert_text(COORDS["customer_address"], summary.get("delivery_address", "N/A"), fontname="helv", fontsize=11)
    page.insert_text(COORDS["delivery_date"], summary.get("requested_delivery_date", "N/A"), fontname="helv", fontsize=11)

    # --- 2. Fill Line Items into the pre-drawn Table ---
    tbl = COORDS["table"]
    current_y = tbl["first_row_y"]
    for item in order_data.get("line_items", []):
        page.insert_text((tbl["col_sku"], current_y), str(item.get("sku", "")), fontname="helv", fontsize=10)
        page.insert_text((tbl["col_prod"], current_y), str(item.get("product_name", "")), fontname="helv", fontsize=10)
        page.insert_text((tbl["col_qty"], current_y), str(item.get("quantity", "")), fontname="helv", fontsize=10)
        page.insert_text((tbl["col_price"], current_y), f"${item.get('unit_price', 0.0):.2f}", fontname="helv", fontsize=10)
        current_y += tbl["row_height"] # Move down for the next item

    # --- 3. Fill Footer Notes and Issues ---
    notes_text = summary.get("notes")
    if notes_text:
        page.insert_text((75, COORDS["notes_start_y"]), notes_text, fontname="helv", fontsize=10)
    
    issues = order_data.get("issues_for_review", [])
    if issues:
        issue_y = COORDS["issues_start_y"]
        for issue in issues:
            issue_text = f"- {issue.get('status')}: {issue.get('details')}"
            page.insert_text((75, issue_y), issue_text, fontname="helv-it", fontsize=9) # Italic for issues
            issue_y += 15 # Move down for the next issue

    # --- 4. Save the new PDF ---
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    safe_customer_name = summary.get("customer_name", "ORDER").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    output_path = os.path.join(output_folder, f"FILLED_SO_{safe_customer_name}_{timestamp}.pdf")
    
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    print(f"📄 Successfully created filled PDF: {output_path}")
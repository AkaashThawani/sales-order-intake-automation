import fitz  # PyMuPDF
import json
import os
import platform # Import the platform module
from datetime import datetime

# --- USING YOUR FINAL, FINE-TUNED COORDINATES ---
COORDS = {
    # Unchanged, this looks good.
    "customer_name": (250, 145),
    # Moved Y-coordinates down by 3 points to align better with labels.
    "customer_address": (250, 180),
    "delivery_date": (250, 210),
    "table": {
        # This Y-coordinate is good.
        "first_row_y": 315, 
        "row_height": 23,
        # Final adjustments to center text within their respective columns.
        "col_sku": 80,      # Moved slightly left
        "col_prod": 200,    # Moved slightly left
        "col_qty": 330,     # Moved significantly left
        "col_price": 468    # Moved significantly left
    },
    "notes_start_y": 625,
    "issues_start_y": 685
}

def get_font_paths():
    """Detects the OS and returns the correct paths for standard fonts."""
    os_name = platform.system()
    if os_name == "Windows":
        return {
            "regular": "C:/Windows/Fonts/arial.ttf",
            "bold": "C:/Windows/Fonts/arialbd.ttf",
            "italic": "C:/Windows/Fonts/ariali.ttf"
        }
    elif os_name == "Darwin":  # macOS
        return {
            "regular": "/System/Library/Fonts/Supplemental/Arial.ttf",
            "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "italic": "/System/Library/Fonts/Supplemental/Arial Italic.ttf"
        }
    else:  # Assume Linux
        if os.path.exists("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"):
             return {
                "regular": "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
                "bold": "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
                "italic": "/usr/share/fonts/truetype/msttcorefonts/Arial_Italic.ttf"
            }
        else: # Fallback for systems without MS Core Fonts
            return {
                "regular": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "italic": "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
            }


def fill_sales_order_pdf(json_path: str, template_path: str, output_folder="output"):
    """
    Reads a processed order from a JSON file and fills out a PDF template.
    """
    try:
        with open(json_path, 'r') as f:
            order_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: JSON file not found at {json_path}")
        return

    doc = fitz.open(template_path)
    page = doc[0]

    # --- FONT REGISTRATION: Now Cross-Platform! ---
    try:
        fonts = get_font_paths()
        page.insert_font(fontname="helv-reg", fontfile=fonts["regular"])
        page.insert_font(fontname="helv-b", fontfile=fonts["bold"])
        page.insert_font(fontname="helv-i", fontfile=fonts["italic"])
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not load system fonts. Please ensure standard fonts are available. Error: {e}")
        return

    # --- 1. Fill Header Info ---
    summary = order_data.get("sales_order_summary", {})
    page.insert_text(COORDS["customer_name"], summary.get("customer_name", "N/A"), fontname="helv-reg", fontsize=11)
    page.insert_text(COORDS["customer_address"], summary.get("delivery_address", "N/A"), fontname="helv-reg", fontsize=11)
    page.insert_text(COORDS["delivery_date"], summary.get("requested_delivery_date", "N/A"), fontname="helv-reg", fontsize=11)

    # --- 2. Fill Line Items into the pre-drawn Table ---
    tbl = COORDS["table"]
    current_y = tbl["first_row_y"]
    for item in order_data.get("line_items", []):
        unit_price = item.get('unit_price')
        price_text = f"${unit_price:.2f}" if isinstance(unit_price, (int, float)) else "N/A"
        page.insert_text((tbl["col_sku"], current_y), str(item.get("sku", "")), fontname="helv-reg", fontsize=10)
        page.insert_text((tbl["col_prod"], current_y), str(item.get("product_name", "")), fontname="helv-reg", fontsize=10)
        page.insert_text((tbl["col_qty"], current_y), str(item.get("quantity", "")), fontname="helv-reg", fontsize=10)
        page.insert_text((tbl["col_price"], current_y), price_text, fontname="helv-reg", fontsize=10)
        current_y += tbl["row_height"]

    # --- 3. Fill Footer Notes and Issues ---
    notes_text = summary.get("notes")
    if notes_text:
        page.insert_text((75, COORDS["notes_start_y"]), notes_text, fontname="helv-reg", fontsize=10)
    
    issues = order_data.get("issues_for_review", [])
    if issues:
        page.insert_text((72, COORDS["issues_start_y"]), "Issues for Manual Review:", fontname="helv-b", fontsize=10)
        issue_y = COORDS["issues_start_y"] + 15
        for issue in issues:
            issue_text = f"- {issue.get('status')}: {issue.get('details')}"
            rect = fitz.Rect(75, issue_y, 550, issue_y + 40)
            page.insert_textbox(rect, issue_text, fontname="helv-i", fontsize=9)
            issue_y += 45

    # --- 4. Save the new PDF ---
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    safe_customer_name = str(summary.get("customer_name", "ORDER")).replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    output_path = os.path.join(output_folder, f"FILLED_SO_{safe_customer_name}_{timestamp}.pdf")
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    print(f"📄 Successfully created filled PDF: {output_path}")
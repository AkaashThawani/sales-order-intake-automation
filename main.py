from core.llm_extractor import extract_order_details_from_email
from core.inventory_manager import load_data
from core.decision_engine import process_and_validate_order
from core.consolidation_checker import find_consolidation_opportunities
from core.output_generator import create_sales_order_json
from core.pdf_writer import fill_sales_order_pdf
from test_data.email_samples import CUSTOMER_EMAILS


def run_order_intake_pipeline(email_key: str):
    """
    Runs the full pipeline for a single customer email.
    """
    print(f"--- 🚀 Starting Order Intake Pipeline for Email: '{email_key}' ---")

    # --- Step 1: Get Email ---
    email = CUSTOMER_EMAILS.get(email_key)
    if not email:
        print(f"❌ ERROR: Email key '{email_key}' not found.")
        return

    print(f"📧 Processing email from: {email['sender']}")

    # --- Step 2: Extract data with AI ---
    extracted_data = extract_order_details_from_email(email['body'])
    if not extracted_data:
        print("--- Pipeline halted: AI could not extract a valid order structure. ---")
        return
    print("🤖 AI extraction complete.")

    # --- Step 3: Load ALL data ---
    inventory_df = load_data("data/inventory.csv")
    pending_shipments_df = load_data("data/pending_shipments.csv")
    if inventory_df is None or pending_shipments_df is None:
        print("--- Pipeline halted: A required data file could not be loaded. ---")
        return

    # --- Step 4: Validate and Process Order ---
    final_order_data = process_and_validate_order(extracted_data, inventory_df)
    print("⚖️ Order validation complete.")

    # --- Step 5: Check for Consolidation Opportunities ---
    consolidation_suggestions = find_consolidation_opportunities(
        new_order_address=final_order_data.get("delivery_address"),
        pending_shipments_df=pending_shipments_df
    )
    if consolidation_suggestions:
        print(
            f"🚚 Found {len(consolidation_suggestions)} potential consolidation(s)!")
        final_order_data["consolidation_suggestions"] = consolidation_suggestions

    json_filepath = create_sales_order_json(final_order_data)
    
    # --- Step 6: Fill the PDF form using the generated JSON ---
    if json_filepath:
        print("✍️  Starting PDF generation...")
        fill_sales_order_pdf(
            json_path=json_filepath, 
            template_path="sales_order_template.pdf" # <-- Name of your PDF
        )
    
    # --- Step 7: Generate Final JSON Output ---
    create_sales_order_json(final_order_data)
    
    print(f"--- ✅ Pipeline finished for Email: '{email_key}' ---")

if __name__ == "__main__":
    # --- CHOOSE WHICH EMAIL TO PROCESS HERE ---
    # Available keys are: "email_1", "email_2", "email_3", "email_4", "email_5"
    
    selected_email = "email_1"
    
    run_order_intake_pipeline(email_key=selected_email)
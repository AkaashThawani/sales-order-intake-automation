import json
import os
from core.llm_extractor import extract_order_details_from_email
from core.inventory_manager import load_data
from core.decision_engine import process_and_validate_order
from core.output_generator import create_sales_order_json
from core.pdf_writer import fill_sales_order_pdf

def load_email_from_file(filepath: str):
    """Loads the text content of an email from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ ERROR: Email file not found at {filepath}")
        return None

def run_order_intake_pipeline(email_filepath: str):
    """
    Runs the full pipeline for a single customer email from a file.
    """
    print(f"\n--- 🚀 Starting Order Intake Pipeline for Email: '{os.path.basename(email_filepath)}' ---")

    # --- Step 1: Get Email from file ---
    email_body = load_email_from_file(email_filepath)
    if not email_body:
        return

    # --- Step 2: Extract data with AI ---
    extracted_data = extract_order_details_from_email(email_body)
    if not extracted_data:
        print("--- Pipeline halted: AI could not extract a valid order structure. ---")
        return
    print("🤖 AI extraction complete.")

    # --- Step 3: Load Catalog ---
    inventory_df = load_data("data/Product Catalog.csv")
    if inventory_df is None:
        print("--- Pipeline halted: Could not load inventory data. ---")
        return

    # --- Step 4: Validate and Process Order ---
    final_order_data = process_and_validate_order(extracted_data, inventory_df)
    print("⚖️ Order validation complete.")
    
    # --- Step 5: Generate Final JSON Output ---
    json_filepath = create_sales_order_json(final_order_data)
    if json_filepath:
        print(f"📄 JSON successfully created at: {json_filepath}")
    
    
    # Step 6: Generate PDF
    if json_filepath:
        print("✍️  Starting PDF generation...")
        fill_sales_order_pdf(
            json_path=json_filepath,
            template_path="sales_order_form_full.pdf"
        )
    
    print(f"--- ✅ Pipeline finished for Email: '{os.path.basename(email_filepath)}' ---")

if __name__ == "__main__":
    # Define the list of all test email files
    email_files_to_test = [
        "test_data/sample_email_1.txt",
        "test_data/sample_email_2.txt",
        "test_data/sample_email_3.txt",
        "test_data/sample_email_4.txt",
        "test_data/sample_email_5.txt",
    ]

    # Loop through each file and run the pipeline
    for email_file in email_files_to_test:
        run_order_intake_pipeline(email_filepath=email_file)
        print("-" * 70) # Add a separator for clarity
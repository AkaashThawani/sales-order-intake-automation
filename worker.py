import time
import pandas as pd
import os

# Import the core logic functions from your existing files
from core.llm_extractor import extract_order_details_from_email
from core.decision_engine import process_and_validate_order
from core.output_generator import create_sales_order_json
from core.pdf_writer import fill_sales_order_pdf

# --- CONFIGURATION ---
PRODUCT_CATALOG_PATH = "data/Product Catalog.csv"
PDF_TEMPLATE_PATH = "sales_order_form_full.pdf" # Make sure this file is in the root
OUTPUT_FOLDER = "output"

def load_inventory_data(path: str) -> pd.DataFrame:
    """Loads the product catalog into a pandas DataFrame."""
    print(f"Loading product catalog from: {path}")
    try:
        inventory_df = pd.read_csv(path, dtype=str)
        print("✅ Product catalog loaded successfully into memory.")
        return inventory_df
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: Product catalog not found at {path}. The worker cannot start.")
        # In a real scenario, you might want to send an alert here.
        return None # type: ignore

def process_single_order(email_content: str, inventory_df: pd.DataFrame):
    """
    Runs the full end-to-end pipeline for one order email.
    """
    print("\n----------------------------------------------------")
    print("1. Extracting order details with LLM...")
    extracted_data = extract_order_details_from_email(email_content)
    
    if not extracted_data:
        print("❌ LLM extraction failed. Skipping this order.")
        return

    print("2. Validating order against inventory...")
    validated_order = process_and_validate_order(extracted_data, inventory_df)

    print("3. Generating JSON output file...")
    json_filepath = create_sales_order_json(validated_order, output_folder=OUTPUT_FOLDER)

    if not json_filepath:
        print("❌ Failed to create JSON file. Skipping PDF generation.")
        return
        
    print("4. Generating PDF sales order form...")
    fill_sales_order_pdf(json_filepath, PDF_TEMPLATE_PATH, output_folder=OUTPUT_FOLDER)
    print("✅ Order processing complete.")
    print("----------------------------------------------------\n")


if __name__ == "__main__":
    # Load the inventory ONCE when the worker starts
    inventory_df = load_inventory_data(PRODUCT_CATALOG_PATH)

    if inventory_df is None:
        # If the catalog fails to load, stop the worker.
        exit(1)

    # In a real system, this loop would connect to an email inbox (IMAP).
    # For now, we simulate processing a new order from a file every 30 seconds.
    # We will use an email from your test_data as an example.
    
    # --- SIMULATION SETUP ---
    # Make sure you have this file in your test_data folder
    test_email_path = "test_data/sample_email_2.txt" 
    
    try:
        with open(test_email_path, 'r') as f:
            test_email_content = f.read()
        print(f"Worker started. Will process a sample order from '{test_email_path}' in a loop.")
    except FileNotFoundError:
        print(f"❌ WARNING: Test email not found at '{test_email_path}'. The worker will run but do nothing.")
        test_email_content = None

    # --- MAIN WORKER LOOP ---
    while True:
        if test_email_content:
            print("\nFound new order to process...")
            process_single_order(test_email_content, inventory_df)
        else:
            print("No test email loaded, worker is idle.")
            
        print("Worker is sleeping for 60 seconds...")
        time.sleep(60)
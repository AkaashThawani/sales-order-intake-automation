import json
from core.llm_extractor import extract_product_details_from_email
from core.inventory_manager import load_data
from core.decision_engine import generate_recommendations
from test_data.email_samples import EMAIL_SAMPLES

def run_logistics_app(scenario_key: str):
    """
    Runs the full logistics analysis pipeline for a given email scenario.
    """
    print(f"--- Starting Logistics AI Assistant (TEST MODE) ---")
    print(f"--- Running Scenario: {scenario_key} ---\n")

    # --- Step 1: Get Email from our test data file ---
    email_text = EMAIL_SAMPLES.get(scenario_key)
    
    if not email_text:
        print(f"ERROR: Scenario '{scenario_key}' not found in test_data/email_samples.py.")
        return

    # --- Step 2: Extract Structured Data with Gemini AI ---
    extracted_products = extract_product_details_from_email(email_text)
    
    if not extracted_products:
        print("--- App finished: No valid products were extracted from the email. ---")
        return

    print("\n--- AI Extracted Products ---")
    print(json.dumps(extracted_products, indent=2))
    
    # --- Step 3: Load Inventory and Pending Shipments ---
    inventory_df = load_data("data/inventory.csv")
    pending_shipments_df = load_data("data/pending_shipments.csv")
    if inventory_df is None:
        print("--- App finished: Could not load inventory. Halting process. ---")
        return
        
    # --- Step 4: Generate Actionable Recommendations ---
    final_recommendations = generate_recommendations(
        extracted_products, inventory_df, pending_shipments_df
    )
    
    # --- Step 5: Display the Final Report ---
    print("\n--- Final Logistics Recommendations ---")
    if not final_recommendations:
        print("No recommendations were generated.")
    else:
        for rec in final_recommendations:
            print(f"\n  Product: {rec.get('product')}")
            print(f"    - Status: {rec.get('status')}")
            print(f"    - Recommendation: {rec.get('recommendation')}")
        
    print("\n\n--- App finished ---")


if __name__ == "__main__":
    # --- CHOOSE WHICH SCENARIO TO RUN HERE ---
    # Available keys from test_data/email_samples.py:
    # "scenario_1_simple_and_vague"
    # "scenario_2_multi_product_and_uncertainty"
    # "scenario_3_email_chain_with_corrections"
    # "scenario_4_no_quantities_and_new_item"
    
    selected_scenario = "scenario_2_multi_product_and_uncertainty"
    
    run_logistics_app(scenario_key=selected_scenario)
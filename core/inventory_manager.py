import pandas as pd
from thefuzz import process, fuzz
import re

def load_data(path: str):
    """Loads data from a CSV file, ensuring all columns are read as strings to prevent type errors."""
    try:
        return pd.read_csv(path, dtype=str)
    except FileNotFoundError:
        print(f"❌ ERROR: Data file not found at path: {path}")
        return None

def find_product_matches(requested_name: str, inventory_df: pd.DataFrame, confidence_threshold=90): # Increased threshold
    """
    Finds product matches using a two-tiered approach:
    1. Tries for a high-confidence, exact match in the product name.
    2. If that fails, uses a fuzzy search as a fallback.
    """
    if inventory_df is None or requested_name is None:
        return []

    clean_requested_name = re.sub(r'\s*\([^)]*\)', '', requested_name).strip().lower()

    # --- TIER 1: High-Confidence Exact Match ---
    # Create a lowercase version of the Product_Name column for direct comparison
    inventory_df['Product_Name_Lower'] = inventory_df['Product_Name'].astype(str).str.lower()
    
    # Check for a perfect match
    perfect_match_df = inventory_df[inventory_df['Product_Name_Lower'] == clean_requested_name]
    
    if len(perfect_match_df) == 1:
        # Found one perfect match, no need for fuzzy search!
        product = perfect_match_df.iloc[0].to_dict()
        product['match_confidence'] = 100
        return [product] # Return it as a list with one item

    # --- TIER 2: Fuzzy Search Fallback ---
    # If no single perfect match was found, proceed with the fuzzy search.
    if 'SearchString' not in inventory_df.columns:
        product_names = inventory_df['Product_Name'].astype(str).str.lower()
        descriptions = inventory_df['Description'].astype(str).fillna('').str.lower()
        inventory_df['SearchString'] = product_names + " " + descriptions
    
    matches = process.extractBests(
        clean_requested_name,
        inventory_df['SearchString'],
        scorer=fuzz.WRatio,
        score_cutoff=confidence_threshold, # Use a higher threshold for better accuracy
        limit=5
    )

    if not matches:
        return []

    matched_products = []
    for match_tuple in matches:
        product_details = inventory_df.iloc[match_tuple[2]].to_dict()
        
        product_details['Available_in_Stock'] = pd.to_numeric(product_details.get('Available_in_Stock'), errors='coerce')
        product_details['Min_Order_Quantity'] = pd.to_numeric(product_details.get('Min_Order_Quantity'), errors='coerce')
        product_details['Price'] = pd.to_numeric(product_details.get('Price'), errors='coerce')
        
        product_details['match_confidence'] = match_tuple[1]
        matched_products.append(product_details)

    return matched_products
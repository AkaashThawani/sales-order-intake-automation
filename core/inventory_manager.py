import pandas as pd
from thefuzz import process, fuzz
import re

def load_data(path: str):
    """Loads data from a CSV file, ensuring all columns are read as strings to prevent type errors."""
    try:
        return pd.read_csv(path, dtype=str)
    except FileNotFoundError:
        print(f"ERROR: Data file not found at path: {path}")
        return None

def find_product_matches(requested_name: str, inventory_df: pd.DataFrame, confidence_threshold=85): # Reset threshold to 85
    """
    Finds potential product matches from the inventory using fuzzy string matching.
    This version is robust and includes definitive debugging prints.
    """
    if inventory_df is None or requested_name is None:
        return []

    # 1. Clean the requested name from the AI
    clean_requested_name = re.sub(r'\s*\([^)]*\)', '', requested_name).strip().lower()

    # 2. Prepare the search space from the inventory
    if 'SearchString' not in inventory_df.columns:
        product_names = inventory_df['ProductName'].astype(str).str.lower()
        descriptions = inventory_df['Description'].astype(str).fillna('').str.lower()
        inventory_df['SearchString'] = product_names + " " + descriptions
    
    # 3. Perform the fuzzy search using a more advanced scorer
    matches = process.extractBests(
        clean_requested_name,
        inventory_df['SearchString'],
        scorer=fuzz.WRatio,
        score_cutoff=confidence_threshold, # Using 85 as a balanced default
        limit=5
    )

    if not matches:
        return []

    # 4. Format the results and convert data types back
    matched_products = []
    for match_tuple in matches:
        product_details = inventory_df.iloc[match_tuple[2]].to_dict()
        
        # Convert numeric fields back from string to their proper types
        product_details['CurrentStock'] = pd.to_numeric(product_details.get('CurrentStock'), errors='coerce')
        product_details['MinOrderQty'] = pd.to_numeric(product_details.get('MinOrderQty'), errors='coerce')
        product_details['Price'] = pd.to_numeric(product_details.get('Price'), errors='coerce')
        
        product_details['match_confidence'] = match_tuple[1]
        matched_products.append(product_details)

    return matched_products
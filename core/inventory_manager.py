import pandas as pd
from thefuzz import process, fuzz

def load_data(path: str):
    """Loads data from a CSV file, handling potential errors."""
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        print(f"ERROR: Data file not found at path: {path}")
        return None

def find_product_matches(requested_name: str, inventory_df: pd.DataFrame, confidence_threshold=85):
    """
    Finds potential product matches from the inventory using fuzzy string matching.
    It checks both the ProductName and Description for better results.

    Args:
        requested_name (str): The product name from the email.
        inventory_df (pd.DataFrame): The inventory catalog.
        confidence_threshold (int): The minimum confidence score (0-100) to consider a match.

    Returns:
        A list of dictionary objects, where each dictionary is a potential match.
    """
    if inventory_df is None:
        return []

    # Create a combined search string for each product
    inventory_df['SearchString'] = inventory_df['ProductName'] + " " + inventory_df['Description']
    
    # Use thefuzz to find the best matches from the 'SearchString' column
    # We use a lenient scorer like partial_ratio to find "steel screws" in "Box of 1000, 1-inch steel screws"
    matches = process.extractBests(
        requested_name,
        inventory_df['SearchString'],
        scorer=fuzz.partial_ratio,
        score_cutoff=confidence_threshold,
        limit=5 # Limit to the top 5 potential matches
    )

    if not matches:
        return []

    # Get the full product details for each match
    matched_products = []
    for match_tuple in matches:
        # match_tuple is like ('Small Steel Screws Box of 1000, 1-inch steel screws', 100, 3)
        # where the last element is the index in the original DataFrame
        product_details = inventory_df.iloc[match_tuple[2]].to_dict()
        product_details['match_confidence'] = match_tuple[1] # Add the confidence score
        matched_products.append(product_details)

    return matched_products
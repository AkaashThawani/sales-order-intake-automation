import pandas as pd

def load_data(path: str):
    """Loads data from a CSV file, handling potential errors."""
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        print(f"ERROR: Data file not found at path: {path}")
        return None # Return None if the file doesn't exist

def check_inventory(product_name: str, inventory_df: pd.DataFrame):
    """
    Checks for a product in the inventory dataframe using case-insensitive matching.
    Returns the product's data row if found, otherwise None.
    """
    if inventory_df is None:
        return None
    
    # Use .str.lower() for robust, case-insensitive matching
    match = inventory_df[inventory_df['ProductName'].str.lower() == product_name.lower()]
    
    if not match.empty:
        return match.iloc[0] # Return the first (and likely only) match
    return None
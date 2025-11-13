from thefuzz import fuzz

def find_consolidation_opportunities(new_order_address: str, pending_shipments_df, confidence_threshold=90):
    """
    Checks if a new order's address closely matches any pending shipments.

    Args:
        new_order_address (str): The delivery address of the new order.
        pending_shipments_df (pd.DataFrame): DataFrame of pending shipments.
        confidence_threshold (int): The similarity score required to suggest a match.

    Returns:
        A list of dictionaries, where each dictionary is a pending order that could be consolidated.
    """
    if pending_shipments_df is None or new_order_address is None:
        return []

    potential_matches = []
    
    # Iterate through each unique pending destination
    for destination in pending_shipments_df['Destination'].unique():
        # Compare the new address with the pending destination address
        similarity_score = fuzz.token_sort_ratio(new_order_address, destination)
        
        if similarity_score >= confidence_threshold:
            # If it's a strong match, find all orders going to this destination
            matching_orders = pending_shipments_df[pending_shipments_df['Destination'] == destination]
            
            for index, order in matching_orders.iterrows():
                potential_matches.append({
                    "pending_order_id": order['OrderID'],
                    "similar_address": destination,
                    "match_confidence": similarity_score
                })
    
    return potential_matches
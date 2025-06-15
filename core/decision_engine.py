from .inventory_manager import check_inventory

def generate_recommendations(extracted_products: list, inventory_df, pending_shipments_df):
    """Checks inventory for products and decides on the next action."""
    recommendations = []
    
    for product in extracted_products:
        req_name = product.get('product_name', 'Unknown Product')
        # --- CHANGE HERE: Safely get quantity, it might not exist ---
        req_qty = product.get('quantity')
        
        # --- NEW LOGIC: Handle cases where quantity is missing ---
        if req_qty is None or req_qty <= 0:
            recommendations.append({
                "product": req_name,
                "status": "MISSING_QUANTITY",
                "recommendation": f"Product '{req_name}' was mentioned without a specific quantity. Manual review required."
            })
            continue # Move to the next product

        stock_info = check_inventory(req_name, inventory_df)
        
        if stock_info is None:
            recommendations.append({
                "product": req_name,
                "status": "NOT_FOUND",
                "recommendation": f"Product '{req_name}' not found in inventory. Manual review required."
            })
            continue

        current_stock = stock_info['CurrentStock']
        warehouse = stock_info['Warehouse']
        moq = stock_info['MinOrderQty']
        
        # This logic now only runs for products with a valid quantity
        if req_qty <= current_stock:
            rec_text = f"Ship {req_qty} units directly from {warehouse}."
            if pending_shipments_df is not None and not pending_shipments_df.empty:
                 rec_text += " NOTE: There are other pending shipments; consider consolidating."
            
            recommendations.append({
                "product": req_name, "quantity": req_qty, "status": "IN_STOCK",
                "warehouse": warehouse, "recommendation": rec_text
            })
        elif req_qty > current_stock and current_stock > 0:
            needed = req_qty - current_stock
            order_qty = max(needed, moq)
            recommendations.append({
                "product": req_name, "quantity": req_qty, "status": "PARTIAL_STOCK",
                "warehouse": warehouse, 
                "recommendation": f"Partial stock ({current_stock} units) at {warehouse}. Order an additional {order_qty} units (MOQ is {moq})."
            })
        else: # current_stock is 0
            order_qty = max(req_qty, moq)
            recommendations.append({
                "product": req_name, "quantity": req_qty, "status": "OUT_OF_STOCK",
                "warehouse": warehouse,
                "recommendation": f"Product is out of stock. Order at least {order_qty} units for warehouse {warehouse} (MOQ is {moq})."
            })
            
    return recommendations
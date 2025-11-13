#!/usr/bin/env python3
"""
Script to seed the database with basic orders for testing
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, Order, Customer, LineItem
from sqlalchemy.orm import Session

def create_basic_orders(db: Session):
    """Create basic orders for testing"""

    # Create some customers
    customers_data = [
        {"email": "john.doe@example.com", "name": "John Doe"},
        {"email": "jane.smith@example.com", "name": "Jane Smith"},
        {"email": "bob.wilson@example.com", "name": "Bob Wilson"},
        {"email": "alice.brown@example.com", "name": "Alice Brown"},
    ]

    customers = []
    for customer_data in customers_data:
        customer = Customer(
            email=customer_data["email"],
            name=customer_data["name"]
        )
        db.add(customer)
        customers.append(customer)

    db.flush()  # Get IDs

    # Create some orders
    orders_data = [
        {
            "customer": customers[0],
            "status": "inquiry",
            "delivery_address": "123 Main St, Anytown, USA",
            "delivery_date": "2025-12-01",
            "customer_notes": "Please deliver during business hours",
            "line_items": [
                {"name": "Widget A", "quantity": 5},
                {"name": "Widget B", "quantity": 2},
            ]
        },
        {
            "customer": customers[1],
            "status": "in_process",
            "delivery_address": "456 Oak Ave, Somewhere, USA",
            "delivery_date": "2025-11-15",
            "customer_notes": "Handle with care",
            "line_items": [
                {"name": "Gadget X", "quantity": 10},
            ]
        },
        {
            "customer": customers[2],
            "status": "response",
            "delivery_address": "789 Pine Rd, Elsewhere, USA",
            "delivery_date": "2025-11-20",
            "customer_notes": "Call before delivery",
            "line_items": [
                {"name": "Tool Set", "quantity": 1},
                {"name": "Widget C", "quantity": 3},
            ]
        },
        {
            "customer": customers[3],
            "status": "completed",
            "delivery_address": "321 Elm St, Nowhere, USA",
            "delivery_date": "2025-10-30",
            "customer_notes": "Thank you for the quick service",
            "line_items": [
                {"name": "Widget A", "quantity": 8},
            ]
        },
    ]

    for order_data in orders_data:
        order = Order(
            customer_id=order_data["customer"].id,
            status=order_data["status"],
            delivery_address=order_data["delivery_address"],
            delivery_date=order_data["delivery_date"],
            customer_notes=order_data["customer_notes"],
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        db.add(order)
        db.flush()

        # Add line items
        for item_data in order_data["line_items"]:
            line_item = LineItem(
                order_id=order.id,
                requested_name=item_data["name"],
                requested_quantity=item_data["quantity"]
            )
            db.add(line_item)

    db.commit()
    print(f"✅ Created {len(customers)} customers and {len(orders_data)} orders")

def main():
    """Main function to seed the database"""
    print("🌱 Seeding database with basic orders...")

    db = SessionLocal()
    try:
        create_basic_orders(db)
        print("✅ Database seeded successfully!")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

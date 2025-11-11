#!/usr/bin/env python3
"""
Script to seed the database with dummy data for testing the UI
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, Order, Customer, LineItem, EmailLog, WorkflowTask
from sqlalchemy.orm import Session

def create_dummy_data(db: Session):
    """Create dummy emails for existing orders"""

    # Get existing orders
    orders = db.query(Order).all()
    if not orders:
        print("No orders found. Please run the seeding script first to create orders.")
        return

    print(f"Found {len(orders)} existing orders. Adding emails...")

    # Create dummy emails for each order
    email_templates = [
        "Hi, I would like to place an order for {quantity} units of {product}. Please deliver to {address}. Contact: {email}",
        "Hello, we need {quantity} {product} for our project. Can you provide pricing and availability? Delivery to {address}",
        "Dear Sales Team, Please quote {quantity} {product}. We need delivery by next week to {address}. Best regards, {name}",
        "Following up on our previous conversation about {product}. We need {quantity} units. Please confirm pricing.",
        "Thank you for the quote on {product}. We'd like to proceed with ordering {quantity} units for delivery to {address}.",
    ]

    for order in orders:
        # Get line items for this order
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()
        first_item = line_items[0] if line_items else None

        # Create incoming email (customer inquiry)
        customer_email = EmailLog(
            email_id=f"incoming_{order.id}_{random.randint(1000, 9999)}",
            direction="incoming",
            subject=f"Order Inquiry - {first_item.requested_name if first_item else 'Products'}",
            sender=order.customer.email,
            recipient="sales@company.com",
            workflow_stage="INQUIRY",
            intent_summary="Customer requesting quote or placing order",
            requires_action=True,
            received_at=order.created_at,
            body=random.choice(email_templates).format(
                quantity=first_item.requested_quantity if first_item else 10,
                product=first_item.requested_name if first_item else "widgets",
                address=order.delivery_address,
                email=order.customer.email,
                name=order.customer.name
            )
        )
        db.add(customer_email)

        # For orders that have responses, create outgoing emails
        if order.status in ['response', 'follow_up', 'completed']:
            sales_email = EmailLog(
                email_id=f"outgoing_{order.id}_{random.randint(1000, 9999)}",
                direction="outgoing",
                subject=f"Re: Order Inquiry - {first_item.requested_name if first_item else 'Products'}",
                sender="sales@company.com",
                recipient=order.customer.email,
                workflow_stage="RESPONSE",
                intent_summary="Sales response with quote or confirmation",
                requires_action=False,
                received_at=order.created_at + timedelta(hours=random.randint(1, 24)),
                body=f"Thank you for your inquiry about {first_item.requested_name if first_item else 'our products'}. We'd be happy to provide a quote for {first_item.requested_quantity if first_item else 10} units. Please find our pricing and terms below..."
            )
            db.add(sales_email)

    # Create some workflow tasks
    for order in orders:
        if order.status == 'in_process':
            task = WorkflowTask(
                order_id=order.id,
                task_type='approval_required',
                parameters={'reason': 'Large order value'},
                status='pending',
                created_by='system'
            )
            db.add(task)

    db.commit()
    print("✅ Dummy data created successfully!")

def main():
    """Main function to seed the database"""
    print("🌱 Seeding database with dummy data...")

    db = SessionLocal()
    try:
        create_dummy_data(db)
        print("✅ Database seeded successfully!")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

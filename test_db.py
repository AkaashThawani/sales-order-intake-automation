#!/usr/bin/env python3
"""
Test database connection and contents
"""
import os
import sys

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, Customer, Order, EmailLog

def main():
    print(f"Current working directory: {os.getcwd()}")
    print(f"DATABASE_URL env var: {os.getenv('DATABASE_URL', 'Not set (using default sqlite:///sales_orders.db)')}")

    db = SessionLocal()
    try:
        print(f"\nDatabase file path would be: {os.path.join(os.getcwd(), 'sales_orders.db')}")

        customer_count = db.query(Customer).count()
        order_count = db.query(Order).count()
        email_count = db.query(EmailLog).count()

        print(f"\nActual counts:")
        print(f"Customers: {customer_count}")
        print(f"Orders: {order_count}")
        print(f"Emails: {email_count}")

        if order_count > 0:
            print(f"\nFirst order details:")
            first_order = db.query(Order).first()
            if first_order:
                print(f"  ID: {first_order.id}")
                print(f"  Status: {first_order.status}")
                print(f"  Customer: {first_order.customer.name if first_order.customer else 'None'}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

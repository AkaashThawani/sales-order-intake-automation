#!/usr/bin/env python3
"""
Script to check database contents
"""
from models import SessionLocal, Customer, Order, EmailLog
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    db = SessionLocal()
    try:
        print(f"Customers: {db.query(Customer).count()}")
        print(f"Orders: {db.query(Order).count()}")
        print(f"Emails: {db.query(EmailLog).count()}")

        # Show some sample data
        customers = db.query(Customer).limit(3).all()
        print("\nSample customers:")
        for c in customers:
            print(f"  {c.name} - {c.email}")

        orders = db.query(Order).limit(3).all()
        print("\nSample orders:")
        for o in orders:
            print(
                f"  Order #{o.id} - {o.status} - {o.customer.name if o.customer else 'No customer'}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

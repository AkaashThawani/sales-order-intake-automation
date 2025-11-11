#!/usr/bin/env python3
"""
Script to clear all data from database tables
"""
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, Customer, Order, LineItem, EmailLog, WorkflowTask, WorkflowRule
from sqlalchemy.orm import Session

def clear_all_data(db: Session):
    """Clear all data from all tables"""

    # Delete in order to respect foreign key constraints
    db.query(WorkflowTask).delete()
    db.query(LineItem).delete()
    db.query(EmailLog).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.query(WorkflowRule).delete()

    db.commit()
    print("✅ All data cleared from database")

def main():
    """Main function to clear the database"""
    print("🗑️ Clearing all data from database...")

    db = SessionLocal()
    try:
        clear_all_data(db)
        print("✅ Database cleared successfully!")
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
import os

# Use SQLite for development, easy to switch to PostgreSQL later
# Hardcoded to root directory to avoid path confusion
DATABASE_URL = 'sqlite:///d:/sale-order-automation/sales_orders.db'
engine = create_engine(DATABASE_URL, echo=False)  # Disabled SQL logging

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))

    # Order details
    status = Column(String, default='inquiry')  # inquiry, in_process, db_check, response, follow_up, completed
    delivery_address = Column(Text)
    delivery_date = Column(String)
    customer_notes = Column(Text)

    # Workflow management
    workflow_tasks = Column(JSON)  # List of pending tasks
    human_notes = Column(Text)  # Notes from human operators
    requires_human_review = Column(Boolean, default=False)

    # Rule engine results
    applied_rules = Column(JSON)  # Track which rules were applied
    approval_required = Column(Boolean, default=False)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Email thread tracking
    email_thread_id = Column(String, index=True)
    last_email_subject = Column(String)
    last_email_received = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("LineItem", back_populates="order")
    email_logs = relationship("EmailLog", back_populates="order")
    workflow_tasks_rel = relationship("WorkflowTask", back_populates="order")

class LineItem(Base):
    __tablename__ = 'line_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))

    # Requested product details
    requested_name = Column(String)
    requested_quantity = Column(Integer)

    # Validation results
    status = Column(String)  # VALIDATED, NOT_FOUND, MOQ_NOT_MET, INSUFFICIENT_STOCK, etc.
    issue = Column(Text)

    # Matched product details
    product_code = Column(String)
    product_name = Column(String)
    unit_price = Column(String)
    total_price = Column(String)

    order = relationship("Order", back_populates="line_items")

class EmailLog(Base):
    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)

    # Email metadata
    email_id = Column(String, unique=True)  # IMAP message ID
    direction = Column(String)  # incoming, outgoing
    subject = Column(String)
    sender = Column(String)
    recipient = Column(String)
    body = Column(Text)

    # Email threading headers
    message_id = Column(String)  # RFC 2822 Message-ID header
    references = Column(Text)    # RFC 2822 References header
    in_reply_to = Column(String) # RFC 2822 In-Reply-To header

    # AI Classification results
    workflow_stage = Column(String)  # inquiry, follow_up, response, clarification
    intent_summary = Column(Text)
    requires_action = Column(Boolean, default=True)

    # Related order if detected
    related_order_id = Column(Integer, nullable=True)

    received_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="email_logs")

class WorkflowTask(Base):
    __tablename__ = 'workflow_tasks'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))

    # Task definition
    task_type = Column(String)  # validate_inventory, generate_response, send_email, custom_task
    status = Column(String, default='pending')  # pending, in_progress, completed, failed
    parameters = Column(JSON)  # Task-specific parameters
    result = Column(JSON)  # Task execution result

    # Task metadata
    created_by = Column(String, default='system')  # system or human operator
    priority = Column(Integer, default=1)  # 1=low, 5=high

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    order = relationship("Order", back_populates="workflow_tasks_rel")

class WorkflowRule(Base):
    __tablename__ = 'workflow_rules'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)
    conditions = Column(JSON)  # {"field": "total_quantity", "operator": ">", "value": 10}
    actions = Column(JSON)     # {"action": "require_approval", "message": "Large order"}
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    rule_type = Column(String, default='quantity')

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from datetime import datetime
from models import SessionLocal, Order, Customer, LineItem, EmailLog, WorkflowTask, WorkflowRule, create_tables
from core.workflow_processor import WorkflowProcessor
from core.email_manager import EmailManager
from core.rule_engine import RuleEngine
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

# Create database tables on startup
create_tables()

app = FastAPI(
    title="Sales Order Automation API",
    description="AI-powered sales order processing with automated workflow management",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
workflow_processor = WorkflowProcessor()
email_manager = EmailManager()

# Pydantic models for API requests/responses
class EmailProcessRequest(BaseModel):
    email_content: str
    customer_email: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    customer_email: str
    customer_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    delivery_address: Optional[str]
    delivery_date: Optional[str]
    customer_notes: Optional[str]
    applied_rules: List[Dict[str, Any]] = []
    approval_required: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    line_items: List[Dict[str, Any]] = []
    workflow_tasks: List[Dict[str, Any]] = []

class EmailLogResponse(BaseModel):
    id: int
    email_id: str
    direction: str
    subject: str
    sender: str
    recipient: str
    workflow_stage: Optional[str]
    intent_summary: Optional[str]
    requires_action: bool
    received_at: datetime

class StatsResponse(BaseModel):
    total_orders: int
    orders_by_status: Dict[str, int]
    total_emails: int
    emails_by_stage: Dict[str, int]
    pending_tasks: int
    completed_tasks_today: int

class RuleCreateRequest(BaseModel):
    name: str
    description: str = ""
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    priority: int = 1
    rule_type: str = "quantity"

class RuleResponse(BaseModel):
    id: int
    name: str
    description: str
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    priority: int
    rule_type: str
    is_active: bool
    created_at: datetime

class RuleTestRequest(BaseModel):
    conditions: Dict[str, Any]
    test_metrics: Dict[str, Any]

class OrderStatusUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = None

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Sales Order Automation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "components": {
            "database": "connected",
            "email_manager": "initialized",
            "workflow_processor": "ready"
        }
    }

@app.post("/api/process-email", response_model=OrderResponse)
async def process_email(
    request: EmailProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process an email through the complete workflow"""

    try:
        # Extract subject from email content (first line or default)
        lines = [line.strip() for line in request.email_content.split('\n') if line.strip()]
        subject = lines[0] if lines else "Customer Inquiry"

        # Create email data structure
        email_data = {
            'id': f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'subject': subject,
            'sender': f"{request.customer_email or 'unknown@example.com'}",
            'body': request.email_content,
            'message_id': f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'references': '',
            'received_at': datetime.now()
        }

        # Process through workflow
        result = workflow_processor.process_email(email_data)

        if result['orders_affected']:
            order_id = result['orders_affected'][0]

            # Log the initial email to EmailLog for conversation tracking
            email_log = EmailLog(
                email_id=email_data['id'],
                direction='incoming',
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipient='system@company.com',  # Demo recipient
                body=email_data['body'],
                received_at=email_data['received_at'],
                order_id=order_id,
                workflow_stage='INQUIRY',
                intent_summary='Manual email processing via demo/API',
                requires_action=True
            )
            db.add(email_log)
            db.commit()

            # Get the created order
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found after creation")

            # Run full workflow processing using the SAME database session
            print(f"🚀 Starting workflow processing for order {order_id}")
            try:
                # Process the order through the workflow using the same DB session
                workflow_processor.process_pending_orders_sync(db)
                print(f"✅ Workflow processing completed for order {order_id}")

                # Refresh order data
                db.refresh(order)
                print(f"📊 Order refreshed: status={order.status}")

            except Exception as workflow_error:
                print(f"❌ Workflow processing error: {workflow_error}")
                import traceback
                traceback.print_exc()
                # Continue anyway - order was created successfully

            return _order_to_response(order, db)

        raise HTTPException(status_code=400, detail="Failed to process email")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

def _generate_demo_response(db: Session, order: Order):
    """Generate an automated response for demo purposes"""

    try:
        # Get line items to create response
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()

        if not line_items:
            return  # No items to respond about

        # Create response content
        response_lines = []
        total_value = 0

        for item in line_items:
            if item.status == 'VALIDATED' and item.unit_price and item.total_price:
                response_lines.append(f"- {item.product_name or item.requested_name}: ${item.unit_price} x {item.requested_quantity} = ${item.total_price}")
                try:
                    total_value += float(item.total_price or 0)
                except:
                    pass
            elif item.status == 'NOT_FOUND':
                response_lines.append(f"- {item.requested_name}: Item not found in catalog - will follow up")
            elif item.status == 'MOQ_NOT_MET':
                response_lines.append(f"- {item.requested_name}: Minimum order quantity not met")
            else:
                response_lines.append(f"- {item.requested_name}: Processing - will provide quote shortly")

        response_body = f"""Dear {order.customer.name or 'Valued Customer'},

Thank you for your inquiry! We've processed your order request:

{chr(10).join(response_lines)}

{f"Total estimated value: ${total_value:.2f}" if total_value > 0 else ""}

Please review the details above. If everything looks correct, we can proceed with your order. If you have any questions or need modifications, please let us know.

Best regards,
Sales Team
"""

        # Create outgoing email log
        email_log = EmailLog(
            email_id=f"response_{order.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            direction='outgoing',
            subject=f"Re: {order.last_email_subject or 'Order Inquiry'}",
            sender='sales@company.com',
            recipient=order.customer.email,
            body=response_body,
            received_at=datetime.now(),
            order_id=order.id,
            workflow_stage='RESPONSE',
            intent_summary='Automated response with order details and pricing',
            requires_action=False
        )
        db.add(email_log)

        # Update order status to response
        order.status = 'response'
        order.updated_at = datetime.now()

        db.commit()

    except Exception as e:
        print(f"Error generating demo response: {e}")
        db.rollback()

@app.post("/api/fetch-emails")
async def fetch_emails(background_tasks: BackgroundTasks):
    """Manually trigger email fetching and processing"""
    try:
        background_tasks.add_task(_process_emails_background)
        return {"message": "Email processing started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start email processing: {str(e)}")

def _process_emails_background():
    """Background task to process emails"""
    try:
        # Fetch and process emails
        processed_emails = email_manager.fetch_and_process_emails()

        # Process each email through workflow
        for email_info in processed_emails:
            email_data = email_info['email_data']
            workflow_processor.process_email(email_data)

        print(f"✅ Processed {len(processed_emails)} emails")

    except Exception as e:
        print(f"❌ Error in background email processing: {e}")

@app.post("/api/process-workflow")
async def process_workflow(background_tasks: BackgroundTasks):
    """Manually trigger workflow processing"""
    try:
        background_tasks.add_task(workflow_processor.process_pending_orders)
        return {"message": "Workflow processing started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow processing: {str(e)}")

@app.get("/api/orders", response_model=List[OrderResponse])
async def get_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get orders with optional filtering"""
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    return [_order_to_response(order, db) for order in orders]

@app.get("/api/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get specific order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return _order_to_response(order, db)

@app.get("/api/orders/{order_id}/emails", response_model=List[EmailLogResponse])
async def get_order_emails(order_id: int, db: Session = Depends(get_db)):
    """Get email chain for a specific order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Get emails linked to this order
    emails = db.query(EmailLog).filter(EmailLog.order_id == order_id).order_by(EmailLog.received_at.asc()).all()

    return [_email_to_response(email) for email in emails]

@app.put("/api/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: OrderStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update order status (human intervention)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Validate status
    valid_statuses = ['inquiry', 'in_process', 'db_check', 'response', 'follow_up', 'completed']
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    old_status = order.status
    order.status = request.status
    order.updated_at = datetime.utcnow()

    if request.notes:
        current_notes = order.human_notes or ""
        order.human_notes = current_notes + f"\n\n[{datetime.utcnow()}] Status changed from '{old_status}' to '{request.status}': {request.notes}"

    if request.status == 'completed':
        order.completed_at = datetime.utcnow()

    db.commit()

    return {"message": f"Order {order_id} status updated to {request.status}"}

class AddTaskRequest(BaseModel):
    task_type: str
    parameters: Optional[Dict[str, Any]] = None

@app.post("/api/orders/{order_id}/tasks")
async def add_workflow_task(
    order_id: int,
    request: AddTaskRequest,
    db: Session = Depends(get_db)
):
    """Add a workflow task (human intervention)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Create workflow task
    task = WorkflowTask(
        order_id=order_id,
        task_type=request.task_type,
        parameters=request.parameters or {},
        status='pending',
        created_by='human'
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return {"message": f"Task '{request.task_type}' added to order {order_id}", "task_id": task.id}

@app.get("/api/emails", response_model=List[EmailLogResponse])
async def get_emails(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get email logs"""
    emails = db.query(EmailLog).order_by(EmailLog.received_at.desc()).offset(offset).limit(limit).all()

    return [_email_to_response(email) for email in emails]

@app.delete("/api/emails/{email_id}")
async def delete_email(email_id: str, db: Session = Depends(get_db)):
    """Delete an email log"""
    email = db.query(EmailLog).filter(EmailLog.email_id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    db.delete(email)
    db.commit()

    return {"message": f"Email {email_id} deleted successfully"}

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    # Order stats
    total_orders = db.query(Order).count()
    orders_by_status = {}
    for status in ['inquiry', 'in_process', 'db_check', 'response', 'follow_up', 'completed']:
        orders_by_status[status] = db.query(Order).filter(Order.status == status).count()

    # Email stats
    total_emails = db.query(EmailLog).count()
    emails_by_stage = {}
    for stage in ['INQUIRY', 'FOLLOW_UP', 'RESPONSE', 'CLARIFICATION']:
        emails_by_stage[stage] = db.query(EmailLog).filter(EmailLog.workflow_stage == stage).count()

    # Task stats
    pending_tasks = db.query(WorkflowTask).filter(WorkflowTask.status == 'pending').count()

    # Completed tasks today
    today = datetime.utcnow().date()
    completed_tasks_today = db.query(WorkflowTask).filter(
        WorkflowTask.status == 'completed',
        WorkflowTask.completed_at >= today
    ).count()

    return StatsResponse(
        total_orders=total_orders,
        orders_by_status=orders_by_status,
        total_emails=total_emails,
        emails_by_stage=emails_by_stage,
        pending_tasks=pending_tasks,
        completed_tasks_today=completed_tasks_today
    )

# Rule Management Endpoints
@app.post("/api/rules", response_model=RuleResponse)
async def create_rule(rule: RuleCreateRequest, db: Session = Depends(get_db)):
    """Create a new business rule"""
    try:
        rule_engine = RuleEngine(db)
        rule_id = rule_engine.create_rule(
            name=rule.name,
            conditions=rule.conditions,
            actions=rule.actions,
            description=rule.description,
            priority=rule.priority,
            rule_type=rule.rule_type
        )

        # Get the created rule
        created_rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
        return _rule_to_response(created_rule)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")

@app.get("/api/rules", response_model=List[RuleResponse])
async def get_rules(db: Session = Depends(get_db)):
    """Get all active rules"""
    rule_engine = RuleEngine(db)
    rules_data = rule_engine.get_active_rules()

    # Convert to RuleResponse format
    rules = []
    for rule_data in rules_data:
        rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_data["id"]).first()
        if rule:
            rules.append(_rule_to_response(rule))

    return rules

@app.get("/api/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific rule"""
    rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return _rule_to_response(rule)

@app.put("/api/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, rule_update: RuleCreateRequest, db: Session = Depends(get_db)):
    """Update an existing rule"""
    rule_engine = RuleEngine(db)
    success = rule_engine.update_rule(rule_id, rule_update.dict())

    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Get updated rule
    updated_rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
    return _rule_to_response(updated_rule)

@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """Deactivate a rule"""
    rule_engine = RuleEngine(db)
    success = rule_engine.deactivate_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {"message": f"Rule {rule_id} deactivated"}

@app.post("/api/rules/test")
async def test_rule(request: RuleTestRequest):
    """Test a rule against sample metrics"""
    try:
        rule_engine = RuleEngine()  # No DB needed for testing
        result = rule_engine.test_rule(request.conditions, request.test_metrics)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule test failed: {str(e)}")

@app.get("/api/rules/stats")
async def get_rule_stats(db: Session = Depends(get_db)):
    """Get rule statistics"""
    rule_engine = RuleEngine(db)
    stats = rule_engine.get_rule_statistics()
    return stats

def _order_to_response(order: Order, db: Session) -> OrderResponse:
    """Convert Order model to API response"""
    # Get line items
    line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()
    line_items_data = [{
        'id': item.id,
        'requested_name': item.requested_name,
        'requested_quantity': item.requested_quantity,
        'status': item.status,
        'issue': item.issue,
        'product_code': item.product_code,
        'product_name': item.product_name,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in line_items]

    # Get workflow tasks
    tasks = db.query(WorkflowTask).filter(WorkflowTask.order_id == order.id).all()
    tasks_data = [{
        'id': task.id,
        'task_type': task.task_type,
        'status': task.status,
        'parameters': task.parameters,
        'result': task.result,
        'created_by': task.created_by,
        'created_at': task.created_at,
        'completed_at': task.completed_at
    } for task in tasks]

    return OrderResponse(
        id=order.id,
        customer_email=order.customer.email if order.customer else "unknown",
        customer_name=order.customer.name if order.customer else None,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
        delivery_address=order.delivery_address,
        delivery_date=order.delivery_date,
        customer_notes=order.customer_notes,
        applied_rules=order.applied_rules or [],
        approval_required=order.approval_required or False,
        approved_by=order.approved_by,
        approved_at=order.approved_at,
        line_items=line_items_data,
        workflow_tasks=tasks_data
    )

def _email_to_response(email: EmailLog) -> EmailLogResponse:
    """Convert EmailLog model to API response"""
    return EmailLogResponse(
        id=email.id,
        email_id=email.email_id,
        direction=email.direction,
        subject=email.subject,
        sender=email.sender,
        recipient=email.recipient,
        workflow_stage=email.workflow_stage,
        intent_summary=email.intent_summary,
        requires_action=email.requires_action,
        received_at=email.received_at
    )

def _rule_to_response(rule: WorkflowRule) -> RuleResponse:
    """Convert WorkflowRule model to API response"""
    return RuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        conditions=rule.conditions,
        actions=rule.actions,
        priority=rule.priority,
        rule_type=rule.rule_type,
        is_active=rule.is_active,
        created_at=rule.created_at
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

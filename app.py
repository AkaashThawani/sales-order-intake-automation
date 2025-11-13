from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from datetime import datetime
from dotenv import load_dotenv
from models import SessionLocal, Order, Customer, LineItem, EmailLog, WorkflowTask, WorkflowRule, create_tables
from core.workflow_processor import WorkflowProcessor
from core.email_manager import EmailManager
from core.rule_engine import RuleEngine
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

# Load environment variables
load_dotenv()

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
    order_id: Optional[int] = None

    class Config:
        extra = "allow"  # Allow extra fields in the request

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
    body: Optional[str]
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

class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    rule_type: Optional[str] = None
    is_active: Optional[bool] = None

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

class EmailResponseRequest(BaseModel):
    response_content: str
    subject: Optional[str] = None
    reply_to_message_id: Optional[str] = None

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

        # Get customer email - for follow-ups, use existing order's customer email
        if request.order_id:
            print(f"🔍 Looking up order_id: {request.order_id} (type: {type(request.order_id)})")
            # For follow-up emails, get customer email from existing order
            existing_order = db.query(Order).filter(Order.id == request.order_id).first()
            print(f"📋 Found existing order: {existing_order}")
            if not existing_order:
                raise HTTPException(status_code=404, detail=f"Order {request.order_id} not found")
            if not existing_order.customer:
                raise HTTPException(status_code=404, detail=f"Order {request.order_id} has no associated customer")
            customer_email = existing_order.customer.email
            print(f"📧 Using customer email from existing order: {customer_email}")
        else:
            # For new inquiries, extract email from content
            customer_email = email_manager.extract_email_from_content(request.email_content)
            if not customer_email:
                raise HTTPException(status_code=400, detail="Customer email not found in email content")

        # Create email data structure
        email_data = {
            'id': f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'subject': subject,
            'sender': customer_email,  # Use extracted or provided email
            'body': request.email_content,
            'message_id': f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'references': '',
            'received_at': datetime.now()
        }

        # Process through workflow (with explicit order_id if provided)
        result = workflow_processor.process_email(email_data, explicit_order_id=request.order_id)

        if result['orders_affected']:
            order_id = result['orders_affected'][0]

            # Log the email to EmailLog for conversation tracking
            email_log = EmailLog(
                email_id=email_data['id'],
                direction='incoming',
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipient='system@company.com',  # Demo recipient
                body=email_data['body'],
                received_at=email_data['received_at'],
                order_id=order_id,
                workflow_stage='INQUIRY' if not request.order_id else 'CLARIFICATION',
                intent_summary='Manual email processing via demo/API' + (' with explicit order_id' if request.order_id else ''),
                requires_action=True
            )
            db.add(email_log)
            db.commit()

            # Get the order
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found after creation")

            # Run workflow processing for the order
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
                # Continue anyway

            return _order_to_response(order, db)

        raise HTTPException(status_code=400, detail="Failed to process email")

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ CRITICAL ERROR in process_email: {str(e)}")
        print(f"📋 Full traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}\n\nTraceback: {error_details}")

def _generate_demo_response(db: Session, order: Order):
    """Generate an automated response for demo purposes"""

    try:
        # Get line items to create response
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()

        if not line_items:
            return  # No items to respond about

        # Check if this is a clarification response (has recent clarification in notes)
        has_recent_clarification = False
        if order.customer_notes:
            # Look for recent clarification markers in the notes
            clarification_markers = ['[CLARIFICATION', '[QUANTITY UPDATES']
            has_recent_clarification = any(marker in order.upper() for marker in clarification_markers for line in order.customer_notes.split('\n'))

        # Create response content
        validated_items = []
        issues_items = []
        total_value = 0

        for item in line_items:
            if item.status == 'VALIDATED' and item.unit_price and item.total_price:
                validated_items.append({
                    'name': item.product_name or item.requested_name,
                    'quantity': item.requested_quantity,
                    'unit_price': float(item.unit_price or 0),
                    'total_price': float(item.total_price or 0)
                })
                total_value += float(item.total_price or 0)
            elif item.status == 'NOT_FOUND':
                issues_items.append(f"- {item.requested_name}: Item not found in catalog - will follow up")
            elif item.status == 'MOQ_NOT_MET':
                issues_items.append(f"- {item.requested_name}: Minimum order quantity not met")
            else:
                issues_items.append(f"- {item.requested_name}: Processing - will provide quote shortly")

        # Build professional response based on context
        customer_name = order.customer.name or 'Valued Customer'

        if has_recent_clarification:
            # This is a response to a clarification
            intro = f"Dear {customer_name},\n\nThank you for your clarification! I've updated your order based on your feedback."
        else:
            # This is an initial response
            intro = f"Dear {customer_name},\n\nThank you for your order inquiry! I've processed your request and here's the current status."

        # Build order summary
        order_summary = "\n\n📋 **Order Summary:**\n"

        if validated_items:
            order_summary += "\n✅ **Confirmed Items:**\n"
            for item in validated_items:
                order_summary += f"• {item['name']}: {item['quantity']} × ${item['unit_price']:.2f} = ${item['total_price']:.2f}\n"

            if total_value > 0:
                order_summary += f"\n💰 **Total Estimated Value:** ${total_value:.2f}\n"

        if issues_items:
            order_summary += f"\n⚠️ **Items Needing Attention:**\n{chr(10).join(issues_items)}\n"

        # Add next steps
        if validated_items and not issues_items:
            next_steps = "\n🎉 **Great news!** All items in your order are ready to proceed. We'll prepare your sales order documentation and send it for final approval.\n\nPlease review the details above. If everything looks correct, we can move forward with processing your order."
        elif issues_items:
            next_steps = "\n📝 **Next Steps:** Please review the items marked for attention above and let us know how you'd like to proceed. We're here to help resolve any outstanding issues."
        else:
            next_steps = "\n📝 **Next Steps:** We're working on getting quotes for your requested items. We'll follow up soon with pricing and availability information."

        closing = "\n\nIf you have any questions or need modifications, please don't hesitate to let us know.\n\nBest regards,\nSales Team\nABC Coffee Company"

        response_body = intro + order_summary + next_steps + closing

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
            intent_summary='Professional automated response with order details and next steps',
            requires_action=False
        )
        db.add(email_log)

        # Update order status to response
        order.status = 'response'
        order.updated_at = datetime.now()

        db.commit()

    except Exception as e:
        print(f"Error generating demo response: {e}")
        import traceback
        traceback.print_exc()
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

@app.get("/api/emails/conversations", response_model=List[Dict[str, Any]])
async def get_email_conversations(db: Session = Depends(get_db)):
    """Get email conversations grouped by order"""
    # Get all emails grouped by order_id
    emails_by_order = {}
    all_emails = db.query(EmailLog).order_by(EmailLog.received_at.desc()).all()

    for email in all_emails:
        order_id = email.order_id
        if order_id not in emails_by_order:
            emails_by_order[order_id] = []
        emails_by_order[order_id].append(_email_to_response(email))

    # Convert to conversation format
    conversations = []
    for order_id, emails in emails_by_order.items():
        if order_id:  # Only include emails that belong to orders
            order = db.query(Order).filter(Order.id == order_id).first()
            latest_email = emails[0]  # Already sorted by received_at desc

            conversation = {
                "order_id": order_id,
                "customer_name": order.customer.name if order and order.customer else "Unknown",
                "customer_email": order.customer.email if order and order.customer else "unknown@example.com",
                "subject": latest_email.subject,
                "latest_email_date": latest_email.received_at,
                "email_count": len(emails),
                "status": order.status if order else "unknown",
                "direction": latest_email.direction,
                "workflow_stage": order.status if order else "unknown",  # Use current order status
                "requires_action": latest_email.requires_action
            }
            conversations.append(conversation)

    # Sort by latest email date
    conversations.sort(key=lambda x: x["latest_email_date"], reverse=True)

    return conversations

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

    # Handle approval when status is set to 'response' with approval notes
    if request.status == 'response' and request.notes and 'approved' in request.notes.lower():
        order.approved_by = 'manager'  # In a real app, this would be the current user
        order.approved_at = datetime.utcnow()
        order.approval_required = False  # Clear the approval requirement

    if request.notes:
        current_notes = order.human_notes or ""
        order.human_notes = current_notes + f"\n\n[{datetime.utcnow()}] Status changed from '{old_status}' to '{request.status}': {request.notes}"

    # Update workflow_stage for all emails in this order to reflect new order status
    email_logs = db.query(EmailLog).filter(EmailLog.order_id == order_id).all()
    for email_log in email_logs:
        # Update email workflow_stage to match new order status
        email_log.workflow_stage = request.status

    if request.status == 'completed':
        order.completed_at = datetime.utcnow()

    db.commit()

    return {"message": f"Order {order_id} status updated to {request.status}"}

@app.get("/api/orders/{order_id}/generate-pdf")
async def generate_order_pdf(order_id: int, db: Session = Depends(get_db)):
    """Generate a PDF for an order using PyMuPDF"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        import fitz  # PyMuPDF
        from io import BytesIO

        # Get line items
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()

        # Create a new PDF document
        doc = fitz.open()
        page = doc.new_page()

        # Set up fonts and colors
        font_size_title = 24
        font_size_header = 14
        font_size_normal = 11
        font_size_small = 9

        # Colors
        black = (0, 0, 0)
        gray = (0.5, 0.5, 0.5)
        light_gray = (0.9, 0.9, 0.9)

        # Page dimensions
        page_width = page.rect.width
        page_height = page.rect.height
        margin = 50
        y_position = margin

        # Company Header - Center manually (approximate centering)
        company_text = "ABC Coffee Company"
        # Approximate centering - ABC Coffee Company is about 200 units wide at size 24
        x_center = (page_width - 200) / 2
        page.insert_text((x_center, y_position), company_text,
                        fontsize=font_size_title, color=black)
        y_position += 40

        order_title = f"Sales Order #{order.id}"
        # Approximate centering - Sales Order #123 is about 150 units wide at size 14
        x_title_center = (page_width - 150) / 2
        page.insert_text((x_title_center, y_position), order_title,
                        fontsize=font_size_header, color=black)
        y_position += 30

        # Draw header line
        page.draw_line((margin, y_position), (page_width - margin, y_position),
                      color=black, width=2)
        y_position += 20

        # Order Information
        page.insert_text((margin, y_position), "Order Information:",
                        fontsize=font_size_header, color=black)
        y_position += 20

        order_info = [
            f"Customer: {order.customer.name if order.customer else 'N/A'}",
            f"Email: {order.customer.email if order.customer else 'N/A'}",
            f"Order Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Status: {order.status.replace('_', ' ').title()}"
        ]

        if order.delivery_address:
            order_info.append(f"Delivery Address: {order.delivery_address}")
        if order.delivery_date:
            order_info.append(f"Delivery Date: {order.delivery_date}")

        for info in order_info:
            page.insert_text((margin + 20, y_position), info,
                           fontsize=font_size_normal, color=black)
            y_position += 15

        y_position += 20

        # Order Items Table
        page.insert_text((margin, y_position), "Order Items:",
                        fontsize=font_size_header, color=black)
        y_position += 20

        # Table headers
        headers = ["Item", "Quantity", "Unit Price", "Total"]
        col_widths = [200, 80, 80, 80]
        col_positions = [margin]
        for width in col_widths[:-1]:
            col_positions.append(col_positions[-1] + width)

        # Draw table header background
        header_height = 20
        page.draw_rect(fitz.Rect(margin, y_position - 5, page_width - margin, y_position + header_height - 5),
                      color=light_gray, fill=light_gray)

        # Table headers
        for i, header in enumerate(headers):
            page.insert_text((col_positions[i] + 5, y_position + 10), header,
                           fontsize=font_size_normal, color=black)

        y_position += header_height + 5

        # Table rows
        total_amount = 0
        for item in line_items:
            unit_price = float(item.unit_price or 0)
            quantity = item.requested_quantity
            total = float(item.total_price or 0)
            total_amount += total

            row_data = [
                item.product_name or item.requested_name,
                str(quantity),
                f"${unit_price:.2f}",
                f"${total:.2f}"
            ]

            # Draw row background (alternating)
            if line_items.index(item) % 2 == 0:
                page.draw_rect(fitz.Rect(margin, y_position - 3, page_width - margin, y_position + 12),
                              color=(0.98, 0.98, 0.98), fill=(0.98, 0.98, 0.98))

            # Row data
            for i, data in enumerate(row_data):
                page.insert_text((col_positions[i] + 5, y_position + 8), data,
                               fontsize=font_size_normal, color=black)

            y_position += 15

        # Total
        y_position += 10
        total_text = f"Total Amount: ${total_amount:.2f}"
        page.insert_text((page_width - margin - 150, y_position), total_text,
                        fontsize=font_size_header, color=black)
        y_position += 30

        # Footer - Center manually
        footer_y = page_height - 60
        footer_text1 = "Thank you for your business!"
        footer_width1 = len(footer_text1) * font_size_normal * 0.5  # Rough estimate
        x_footer1 = (page_width - footer_width1) / 2
        page.insert_text((x_footer1, footer_y), footer_text1,
                        fontsize=font_size_normal, color=gray)
        footer_y += 15

        footer_text2 = "ABC Coffee Company - Quality Coffee Products"
        footer_width2 = len(footer_text2) * font_size_small * 0.4  # Rough estimate
        x_footer2 = (page_width - footer_width2) / 2
        page.insert_text((x_footer2, footer_y), footer_text2,
                        fontsize=font_size_small, color=gray)

        # Save PDF to bytes
        pdf_bytes = BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        # Return PDF as response
        from fastapi.responses import StreamingResponse

        def iter_pdf():
            yield pdf_bytes.getvalue()

        return StreamingResponse(
            iter_pdf(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Sales_Order_{order.id}.pdf"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@app.post("/api/orders/{order_id}/generate-response")
async def generate_ai_response(order_id: int, db: Session = Depends(get_db)):
    """Generate an AI-powered response for an order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        # Get recent email conversation for context
        recent_emails = db.query(EmailLog).filter(EmailLog.order_id == order_id).order_by(EmailLog.received_at.desc()).limit(10).all()
        recent_emails.reverse()  # Put in chronological order

        # Build conversation context
        conversation_context = []
        for email in recent_emails:
            conversation_context.append({
                'direction': email.direction,
                'subject': email.subject,
                'body': email.body[:500] if email.body else '',  # Limit body length
                'timestamp': email.received_at.isoformat()
            })

        # Get order details
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()
        order_details = {
            'id': order.id,
            'status': order.status,
            'customer_name': order.customer.name,
            'customer_email': order.customer.email,
            'line_items': [{
                'name': item.product_name or item.requested_name,
                'quantity': item.requested_quantity,
                'status': item.status,
                'unit_price': item.unit_price,
                'total_price': item.total_price,
                'issue': item.issue
            } for item in line_items],
            'customer_notes': order.customer_notes,
            'created_at': order.created_at.isoformat()
        }

        # Use AI to generate intelligent response
        from core.llm_extractor import generate_response_suggestion

        ai_response = generate_response_suggestion(
            order_details=order_details,
            conversation_history=conversation_context,
            response_type='customer_response'
        )

        # Generate subject line
        latest_email = recent_emails[-1] if recent_emails else None
        if latest_email and latest_email.direction == 'incoming':
            base_subject = latest_email.subject or "Order Inquiry"
            subject = f"Re: {base_subject}" if not base_subject.startswith("Re:") else base_subject
        else:
            subject = f"Re: Order #{order.id} Update"

        return {
            'subject': subject,
            'body': ai_response,
            'suggested_actions': ['send_response', 'update_status']
        }

    except Exception as e:
        print(f"Error generating AI response: {e}")
        raise HTTPException(status_code=500, detail=f"AI response generation failed: {str(e)}")

@app.post("/api/orders/{order_id}/respond")
async def send_email_response(
    order_id: int,
    request: EmailResponseRequest,
    db: Session = Depends(get_db)
):
    """Send email response for an order with proper threading"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        # Determine subject - add "Re:" prefix if not already present
        subject = request.subject
        if not subject:
            # Get the latest email subject from the chain
            latest_email = db.query(EmailLog).filter(EmailLog.order_id == order_id).order_by(EmailLog.received_at.desc()).first()
            base_subject = latest_email.subject if latest_email else "Order Inquiry"
            subject = f"Re: {base_subject}" if not base_subject.startswith("Re:") else base_subject

        # Send the email response with threading
        email_manager.send_response_email(
            order_id=order_id,
            subject=subject,
            body=request.response_content,
            reply_to_message_id=request.reply_to_message_id
        )

        # Update order status based on current status
        new_status = 'response' if order.status == 'inquiry' else 'follow_up' if order.status == 'follow_up' else 'response'
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.commit()

        return {"message": f"Email response sent successfully. Order status updated to {new_status}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email response: {str(e)}")

def _generate_fallback_response(order: Order, db: Session):
    """Generate a basic fallback response when AI fails"""
    line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()

    validated_items = [item for item in line_items if item.status == 'VALIDATED']
    issues_items = [item for item in line_items if item.status != 'VALIDATED']

    response = f"Dear {order.customer.name or 'Valued Customer'},\n\n"

    if validated_items:
        response += "Thank you for your order inquiry. Here are the items we've confirmed:\n\n"
        for item in validated_items:
            response += f"• {item.product_name or item.requested_name}: {item.requested_quantity} × ${item.unit_price} = ${item.total_price}\n"
        response += "\n"
    else:
        response += "Thank you for your order inquiry. We're processing your request.\n\n"

    if issues_items:
        response += "Items needing attention:\n"
        for item in issues_items:
            response += f"• {item.requested_name}: {item.issue or 'Under review'}\n"
        response += "\n"

    response += "Please let us know if you have any questions.\n\nBest regards,\nSales Team"

    return {
        'subject': f"Re: Order #{order.id} Update",
        'body': response,
        'suggested_actions': ['send_response']
    }

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
async def get_rules(include_inactive: bool = True, db: Session = Depends(get_db)):
    """Get all rules (active and inactive by default)"""
    rule_engine = RuleEngine(db)
    rules_data = rule_engine.get_active_rules(include_inactive=include_inactive)

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
async def update_rule(rule_id: int, rule_update: RuleUpdateRequest, db: Session = Depends(get_db)):
    """Update an existing rule"""
    rule_engine = RuleEngine(db)

    # Get the current rule
    current_rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
    if not current_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Build update data - only include fields that were provided
    update_data = {}
    if rule_update.name is not None:
        update_data['name'] = rule_update.name
    if rule_update.description is not None:
        update_data['description'] = rule_update.description
    if rule_update.conditions is not None:
        update_data['conditions'] = rule_update.conditions
    if rule_update.actions is not None:
        update_data['actions'] = rule_update.actions
    if rule_update.priority is not None:
        update_data['priority'] = rule_update.priority
    if rule_update.rule_type is not None:
        update_data['rule_type'] = rule_update.rule_type
    if rule_update.is_active is not None:
        update_data['is_active'] = rule_update.is_active

    success = rule_engine.update_rule(rule_id, update_data)

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
        body=email.body,
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

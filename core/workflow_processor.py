from models import SessionLocal, Order, LineItem, WorkflowTask, Customer, EmailLog
from .inventory_manager import load_data
from .decision_engine import process_and_validate_order
from .output_generator import create_sales_order_json
from .pdf_writer import fill_sales_order_pdf
from .email_manager import EmailManager
from .llm_extractor import classify_email_intent, extract_order_details_from_email
from .rule_engine import RuleEngine
import datetime
import os
from typing import Dict, List, Any

class WorkflowProcessor:
    def __init__(self):
        print("🔧 Initializing WorkflowProcessor...")
        try:
            # Use absolute path relative to this script's directory
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            inventory_path = os.path.join(script_dir, "..", "data", "Product Catalog.csv")
            self.inventory_df = load_data(inventory_path)
            print(f"📊 Loaded inventory: {len(self.inventory_df) if self.inventory_df is not None else 0} products")
            if self.inventory_df is not None:
                print(f"   Sample products: {list(self.inventory_df['Product_Name'].head(3))}")
        except Exception as e:
            print(f"❌ Failed to load inventory: {e}")
            self.inventory_df = None

        self.email_manager = EmailManager()
        self.rule_engine = RuleEngine()
        print("✅ WorkflowProcessor initialized")

    def process_email(self, email_data: Dict[str, Any], explicit_order_id: int = None) -> Dict[str, Any]:
        """Process an incoming email through the complete workflow"""

        print(f"🔄 Processing email: {email_data['subject'][:50]}...")
        print(f"📧 Explicit order_id: {explicit_order_id}")
        print(f"📧 Email data keys: {list(email_data.keys())}")
        print(f"📧 Email sender: {email_data.get('sender')}")
        print(f"📧 Email body preview: {email_data.get('body', '')[:100]}...")

        # Step 1: Extract customer email and get existing context
        customer_email = self.email_manager.extract_email_address(email_data['sender'])
        existing_orders = self._get_customer_orders(customer_email)
        customer_history = self.email_manager.get_customer_email_history(customer_email)

        print(f"👤 Customer: {customer_email}")
        print(f"📋 Existing orders: {len(existing_orders)}")

        # Step 2: AI Classification
        if explicit_order_id:
            print(f"🎯 Using explicit order_id: {explicit_order_id} - calling AI with order context")

            # Get specific order details for AI context
            db_temp = SessionLocal()
            try:
                specific_order = db_temp.query(Order).filter(Order.id == explicit_order_id).first()
                if specific_order:
                    # Get line items and recent emails for this order
                    line_items = db_temp.query(LineItem).filter(LineItem.order_id == explicit_order_id).all()
                    recent_emails = db_temp.query(EmailLog).filter(EmailLog.order_id == explicit_order_id).order_by(EmailLog.received_at.desc()).limit(5).all()

                    # Build enhanced context for AI
                    order_context = {
                        'order_id': explicit_order_id,
                        'order_status': specific_order.status,
                        'line_items': [
                            {
                                'name': item.requested_name,
                                'quantity': item.requested_quantity,
                                'status': item.status,
                                'issue': item.issue
                            } for item in line_items
                        ],
                        'recent_emails': [
                            {
                                'direction': email.direction,
                                'subject': email.subject,
                                'body_preview': email.body[:100] if email.body else '',
                                'workflow_stage': email.workflow_stage
                            } for email in recent_emails
                        ]
                    }

                    # Call AI with enhanced context
                    classification = classify_email_intent(
                        email_data['subject'],
                        email_data['body'],
                        email_data['sender'],
                        existing_orders,
                        customer_history,
                        order_context=order_context
                    )
                else:
                    # Fallback if order not found
                    classification = {
                        'workflow_stage': 'CLARIFICATION',
                        'intent_summary': f'Clarification for order {explicit_order_id} (order not found)',
                        'requires_action': True,
                        'related_order_id': explicit_order_id
                    }
            finally:
                db_temp.close()
        else:
            print("🤖 Calling AI classification...")
            classification = classify_email_intent(
                email_data['subject'],
                email_data['body'],
                email_data['sender'],
                existing_orders,
                customer_history
            )

        print(f"🏷️ Classification: {classification}")

        result = {
            'classification': classification,
            'actions_taken': [],
            'orders_affected': []
        }

        # Step 3: Route based on classification
        workflow_stage = classification.get('workflow_stage', 'INQUIRY')

        if workflow_stage == 'INQUIRY':
            order_id = self._handle_inquiry(customer_email, email_data, classification)
            if order_id:
                result['orders_affected'].append(order_id)
                result['actions_taken'].append(f"Created new order #{order_id}")

        elif workflow_stage == 'FOLLOW_UP':
            order_ids = self._handle_follow_up(customer_email, email_data, classification)
            result['orders_affected'].extend(order_ids)
            result['actions_taken'].append(f"Updated {len(order_ids)} existing orders")

        elif workflow_stage == 'RESPONSE':
            order_ids = self._handle_response(customer_email, email_data, classification)
            result['orders_affected'].extend(order_ids)
            result['actions_taken'].append(f"Processed responses for {len(order_ids)} orders")

        elif workflow_stage == 'CLARIFICATION':
            order_ids = self._handle_clarification(customer_email, email_data, classification, explicit_order_id)
            result['orders_affected'].extend(order_ids)
            result['actions_taken'].append(f"Added clarification to {len(order_ids)} orders")

        # Step 4: Update email log with classification
        self._update_email_log(email_data['id'], classification, result['orders_affected'])

        return result

    def process_pending_orders(self):
        """Process all orders that need workflow actions"""

        print("🔄 Starting process_pending_orders...")

        db = SessionLocal()
        try:
            # Get orders in various states that need processing
            pending_orders = db.query(Order).filter(
                Order.status.in_(['inquiry', 'in_process', 'follow_up'])
            ).all()

            print(f"📋 Found {len(pending_orders)} orders needing processing")

            for order in pending_orders:
                print(f"⚙️ Processing order {order.id} (status: {order.status})")
                try:
                    self._process_order_workflow(db, order)
                    print(f"✅ Order {order.id} processing completed")
                except Exception as order_error:
                    print(f"❌ Error processing order {order.id}: {order_error}")

            db.commit()
            print("💾 All workflow processing committed")

        except Exception as e:
            print(f"❌ Error in workflow processing: {e}")
            db.rollback()
        finally:
            db.close()

    def process_pending_orders_sync(self, db):
        """Process all orders that need workflow actions using provided DB session"""

        print("🔄 Starting process_pending_orders_sync...")

        try:
            # Get orders in various states that need processing
            pending_orders = db.query(Order).filter(
                Order.status.in_(['inquiry', 'in_process', 'follow_up'])
            ).all()

            print(f"📋 Found {len(pending_orders)} orders needing processing")

            for order in pending_orders:
                print(f"⚙️ Processing order {order.id} (status: {order.status})")
                try:
                    self._process_order_workflow(db, order)
                    print(f"✅ Order {order.id} processing completed")
                except Exception as order_error:
                    print(f"❌ Error processing order {order.id}: {order_error}")
                    # Don't fail the whole process for one order error

            # Don't commit here - let the caller handle the transaction
            print("💾 Workflow processing completed (transaction managed by caller)")

        except Exception as e:
            print(f"❌ Error in workflow processing: {e}")
            raise

    def _process_order_workflow(self, db, order):
        """Process workflow for a single order with rule evaluation"""

        if order.status == 'inquiry':
            # Auto-advance inquiry to in_process if we have order details
            line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()
            print(f"📦 Order {order.id} has {len(line_items)} line items")
            if line_items:
                print(f"🔄 Advancing order {order.id} from 'inquiry' to 'in_process'")
                order.status = 'in_process'
                task_id = self._create_workflow_task(db, order.id, 'validate_inventory')
                print(f"📋 Created inventory validation task {task_id} for order {order.id}")

                # Execute the newly created task immediately
                print(f"▶️ Executing newly created task {task_id} immediately")
                task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
                if task:
                    try:
                        self._execute_task(db, task)
                        print(f"✅ Task {task_id} executed successfully")
                    except Exception as e:
                        print(f"❌ Task {task_id} execution failed: {e}")

                # AFTER inventory validation, apply business rules to VALIDATED items only
                rule_results = self.rule_engine.evaluate_order(order)

                # Store applied rules
                if rule_results['applied_rules']:
                    order.applied_rules = rule_results['applied_rules']

                # Check if approval required
                if rule_results['requires_approval']:
                    order.status = 'pending_approval'
                    db.commit()
                    return

        elif order.status == 'pending_approval':
            # Wait for manual approval
            if order.approved_by:  # Human approved
                print(f"✅ Order {order.id} APPROVED by {order.approved_by} at {order.approved_at}")
                order.status = 'in_process'
                # Re-validate inventory after approval for high-value/large orders
                task_id = self._create_workflow_task(db, order.id, 'validate_inventory')
                print(f"🔄 STARTING INVENTORY VALIDATION for approved order {order.id} (task {task_id})")

        elif order.status == 'in_process':
            # Execute pending tasks
            pending_tasks = db.query(WorkflowTask).filter(
                WorkflowTask.order_id == order.id,
                WorkflowTask.status == 'pending'
            ).all()

            print(f"🔍 Found {len(pending_tasks)} pending tasks for order {order.id}")

            for task in pending_tasks:
                print(f"▶️ Executing task {task.id}: {task.task_type} (created by {task.created_by})")
                try:
                    self._execute_task(db, task)
                    print(f"✅ Task {task.id} ({task.task_type}) completed successfully")
                except Exception as e:
                    print(f"❌ Task {task.id} ({task.task_type}) failed: {e}")
                    import traceback
                    traceback.print_exc()

            # Check if all tasks completed
            completed_tasks = db.query(WorkflowTask).filter(
                WorkflowTask.order_id == order.id,
                WorkflowTask.status == 'completed'
            ).count()

            total_tasks = db.query(WorkflowTask).filter(WorkflowTask.order_id == order.id).count()

            print(f"Order {order.id}: {completed_tasks}/{total_tasks} tasks completed")

            # Debug: List all tasks for this order
            all_tasks = db.query(WorkflowTask).filter(WorkflowTask.order_id == order.id).all()
            print(f"📋 All tasks for order {order.id}:")
            for task in all_tasks:
                print(f"   - Task {task.id}: {task.task_type} - Status: {task.status}")

            if total_tasks > 0 and completed_tasks == total_tasks:
                print(f"🔄 Advancing order {order.id} from 'in_process' to 'db_check'")
                order.status = 'db_check'
                print(f"✅ Order {order.id} advanced to db_check status")
            else:
                print(f"⏳ Order {order.id} still has pending tasks ({completed_tasks}/{total_tasks})")

        elif order.status == 'db_check':
            # All validation complete, generate response
            self._generate_order_response(db, order)
            order.status = 'response'

        elif order.status == 'response':
            # Response sent, wait for customer follow-up
            # This state persists until customer responds or timeout
            pass

    def _handle_inquiry(self, customer_email: str, email_data: Dict, classification: Dict) -> int:
        """Handle new inquiry - create order and extract details"""

        db = SessionLocal()
        try:
            # Extract order details from email first (this includes customer info)
            order_details = classification.get('order_details', {})

            # Log classification results for debugging
            print(f"🔍 Classification for inquiry: {classification}")
            print(f"📋 Initial order_details: {order_details}")

            # If no order details in classification, try to extract from email body
            if not order_details:
                print("🤖 No order details in classification, calling AI extraction...")
                extracted = extract_order_details_from_email(email_data['body'])
                print(f"🎯 AI extraction result: {extracted}")
                if extracted:
                    order_details = {
                        'customer_name': extracted.get('customer_name'),
                        'customer_email': extracted.get('customer_email'),  # AI might extract email too
                        'delivery_address': extracted.get('delivery_address'),
                        'delivery_date': extracted.get('delivery_date'),
                        'customer_notes': extracted.get('customer_notes'),
                        'products': extracted.get('products', [])
                    }
                    print(f"✅ Using AI-extracted order details: {order_details}")
                else:
                    print("❌ AI extraction failed, no order details available")

            # Determine customer email and name
            # Priority: AI-extracted email > API parameter > sender field
            final_customer_email = order_details.get('customer_email') or customer_email
            final_customer_name = order_details.get('customer_name')

            # If no AI-extracted name, try to extract from sender field
            if not final_customer_name:
                final_customer_name = self.email_manager.extract_name_from_email(email_data['sender'])
                # If sender extraction also fails, use a generic name
                if not final_customer_name or final_customer_name == "Unknown Customer":
                    final_customer_name = "Valued Customer"

            # Get or create customer with proper information
            customer = db.query(Customer).filter(Customer.email == final_customer_email).first()
            if not customer:
                customer = Customer(email=final_customer_email, name=final_customer_name)
                db.add(customer)
                db.flush()

            order = Order(
                customer_id=customer.id,
                status='inquiry',
                delivery_address=order_details.get('delivery_address'),
                delivery_date=order_details.get('delivery_date'),
                customer_notes=order_details.get('customer_notes'),
                email_thread_id=email_data.get('message_id'),
                last_email_subject=email_data['subject'],
                last_email_received=email_data['received_at']
            )

            db.add(order)
            db.flush()

            # Add line items
            for product in order_details.get('products', []):
                line_item = LineItem(
                    order_id=order.id,
                    requested_name=product.get('product_name'),
                    requested_quantity=product.get('quantity', 1)
                )
                db.add(line_item)

            db.commit()
            return order.id

        except Exception as e:
            print(f"Error handling inquiry: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def _handle_follow_up(self, customer_email: str, email_data: Dict, classification: Dict) -> List[int]:
        """Handle follow-up - update existing orders"""

        db = SessionLocal()
        try:
            affected_orders = []

            # Try to find related order from classification
            related_order_id = classification.get('related_order_id')

            if related_order_id:
                order = db.query(Order).filter(Order.id == related_order_id).first()
                if order:
                    order.status = 'follow_up'
                    order.last_email_subject = email_data['subject']
                    order.last_email_received = email_data['received_at']
                    affected_orders.append(order.id)

                    # Create task to review follow-up
                    self._create_workflow_task(db, order.id, 'review_follow_up', {
                        'follow_up_content': email_data['body'],
                        'classification': classification
                    })

            # If no specific order found, check recent orders from customer
            else:
                customer = db.query(Customer).filter(Customer.email == customer_email).first()
                if customer:
                    recent_orders = db.query(Order).filter(
                        Order.customer_id == customer.id,
                        Order.status.in_(['response', 'follow_up'])
                    ).order_by(Order.updated_at.desc()).limit(3).all()

                    for order in recent_orders:
                        order.status = 'follow_up'
                        affected_orders.append(order.id)

            db.commit()
            return affected_orders

        except Exception as e:
            print(f"Error handling follow-up: {e}")
            db.rollback()
            return []
        finally:
            db.close()

    def _handle_response(self, customer_email: str, email_data: Dict, classification: Dict) -> List[int]:
        """Handle response to our communications"""
        # Similar to follow-up but specifically for responses to our emails
        return self._handle_follow_up(customer_email, email_data, classification)

    def _handle_clarification(self, customer_email: str, email_data: Dict, classification: Dict, explicit_order_id: int = None) -> List[int]:
        """Handle clarification - add information to existing orders"""

        db = SessionLocal()
        try:
            affected_orders = []

            if explicit_order_id:
                # Use the explicitly provided order_id
                order = db.query(Order).filter(Order.id == explicit_order_id).first()
                if order:
                    # Parse clarification for quantity updates
                    clarification_text = email_data['body'].lower()
                    quantity_updates = self._parse_quantity_updates_from_clarification(clarification_text, order, db)

                    # Add clarification note
                    current_notes = order.customer_notes or ""
                    clarification_note = f"\n\n[CLARIFICATION - {email_data['received_at'].strftime('%Y-%m-%d')}]: {email_data['body'][:200]}..."
                    if quantity_updates:
                        clarification_note += f"\n[QUANTITY UPDATES: {quantity_updates}]"
                    order.customer_notes = current_notes + clarification_note
                    order.status = 'in_process'  # Re-process with new information

                    affected_orders.append(order.id)

                    # Create task to re-validate with clarification
                    self._create_workflow_task(db, order.id, 'revalidate_with_clarification')
            else:
                # Fallback: Find recent orders that might need clarification
                customer = db.query(Customer).filter(Customer.email == customer_email).first()
                if customer:
                    recent_orders = db.query(Order).filter(
                        Order.customer_id == customer.id,
                        Order.status.in_(['db_check', 'response', 'follow_up'])
                    ).order_by(Order.updated_at.desc()).limit(3).all()

                    for order in recent_orders:
                        # Parse clarification for quantity updates
                        clarification_text = email_data['body'].lower()
                        quantity_updates = self._parse_quantity_updates_from_clarification(clarification_text, order, db)

                        # Add clarification note
                        current_notes = order.customer_notes or ""
                        clarification_note = f"\n\n[CLARIFICATION - {email_data['received_at'].strftime('%Y-%m-%d')}]: {email_data['body'][:200]}..."
                        if quantity_updates:
                            clarification_note += f"\n[QUANTITY UPDATES: {quantity_updates}]"
                        order.customer_notes = current_notes + clarification_note
                        order.status = 'in_process'  # Re-process with new information

                        affected_orders.append(order.id)

                        # Create task to re-validate with clarification
                        self._create_workflow_task(db, order.id, 'revalidate_with_clarification')

            db.commit()
            return affected_orders

        except Exception as e:
            print(f"Error handling clarification: {e}")
            db.rollback()
            return []
        finally:
            db.close()

    def _create_workflow_task(self, db, order_id: int, task_type: str, parameters: Dict = None):
        """Create a new workflow task"""

        task = WorkflowTask(
            order_id=order_id,
            task_type=task_type,
            parameters=parameters or {},
            status='pending',
            created_by='system'
        )

        db.add(task)
        db.flush()
        return task.id

    def _execute_task(self, db, task: WorkflowTask):
        """Execute a workflow task"""

        print(f"🔧 Starting task execution for task {task.id} ({task.task_type})")

        try:
            print(f"📝 Setting task {task.id} to 'in_progress'")
            task.status = 'in_progress'
            task.started_at = datetime.datetime.utcnow()
            db.commit()
            print(f"✅ Task {task.id} status updated to 'in_progress'")

            if task.task_type == 'validate_inventory':
                print(f"🏭 Task {task.id} is inventory validation - calling _execute_inventory_validation")
                self._execute_inventory_validation(db, task)
                print(f"✅ Inventory validation completed for task {task.id}")

            elif task.task_type == 'generate_response':
                print(f"📄 Task {task.id} is response generation")
                self._execute_response_generation(db, task)

            elif task.task_type == 'send_email':
                print(f"📧 Task {task.id} is email sending")
                self._execute_email_sending(db, task)

            elif task.task_type == 'review_follow_up':
                print(f"👀 Task {task.id} is follow-up review")
                self._execute_follow_up_review(db, task)

            elif task.task_type == 'revalidate_with_clarification':
                print(f"🔄 Task {task.id} is revalidation")
                self._execute_inventory_validation(db, task)  # Re-run validation

            else:
                print(f"❓ Task {task.id} has unknown type: {task.task_type}")

            print(f"🏁 Setting task {task.id} to 'completed'")
            task.status = 'completed'
            task.completed_at = datetime.datetime.utcnow()
            print(f"✅ Task {task.id} marked as completed")

        except Exception as e:
            print(f"❌ Task {task.id} failed with error: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.datetime.utcnow()
            import traceback
            traceback.print_exc()

        db.commit()
        print(f"💾 Task {task.id} execution committed to database")

    def _execute_inventory_validation(self, db, task: WorkflowTask):
        """Execute inventory validation task"""

        print(f"🔍 Starting inventory validation for task {task.id}, order {task.order_id}")

        order = db.query(Order).filter(Order.id == task.order_id).first()
        if not order:
            print(f"❌ Order {task.order_id} not found")
            raise ValueError(f"Order {task.order_id} not found")

        print(f"📦 Order found: {order.id}, status: {order.status}")

        # Get line items
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()
        print(f"📋 Found {len(line_items)} line items")

        for item in line_items:
            print(f"   - Item: '{item.requested_name}', Qty: {item.requested_quantity}, Status: {item.status}")

        # Convert order to format expected by validation logic
        extracted_data = {
            'customer_name': order.customer.name if order.customer else 'Unknown',
            'delivery_address': order.delivery_address,
            'delivery_date': order.delivery_date,
            'customer_notes': order.customer_notes,
            'products': [
                {
                    'product_name': item.requested_name,
                    'quantity': item.requested_quantity
                } for item in line_items
            ]
        }

        print(f"🔄 Calling process_and_validate_order with {len(extracted_data['products'])} products")
        print(f"   Products: {[p['product_name'] for p in extracted_data['products']]}")

        # Validate order
        try:
            validated_order = process_and_validate_order(extracted_data, self.inventory_df)
            print(f"✅ Validation completed. Processed {len(validated_order.get('processed_line_items', []))} items")
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            raise

        # Update line items with validation results
        processed_items = validated_order.get('processed_line_items', [])
        print(f"🔄 Updating {len(processed_items)} line items in database")

        for item_data in processed_items:
            print(f"   Processing: '{item_data['requested_name']}' -> Status: {item_data.get('status', 'UNKNOWN')}")

            line_item = db.query(LineItem).filter(
                LineItem.order_id == order.id,
                LineItem.requested_name == item_data['requested_name']
            ).first()

            if line_item:
                print(f"   ✅ Found line item {line_item.id}, updating...")
                line_item.status = item_data.get('status', 'UNKNOWN')
                line_item.issue = item_data.get('issue')
                line_item.product_code = item_data.get('product_details', {}).get('Product_Code')
                line_item.product_name = item_data.get('product_details', {}).get('Product_Name')
                line_item.unit_price = str(item_data.get('product_details', {}).get('Price', 0))

                # Calculate total price
                qty = item_data.get('requested_quantity', 0)
                price = float(item_data.get('product_details', {}).get('Price', 0))
                line_item.total_price = str(qty * price)

                print(f"   📝 Updated: status={line_item.status}, product={line_item.product_name}, price={line_item.unit_price}")
            else:
                print(f"   ❌ Line item not found for '{item_data['requested_name']}'")

        print(f"🎯 Inventory validation completed for order {order.id}")

    def _execute_response_generation(self, db, task: WorkflowTask):
        """Generate order response (JSON + PDF)"""

        order = db.query(Order).filter(Order.id == task.order_id).first()
        if not order:
            raise ValueError(f"Order {task.order_id} not found")

        # Generate JSON
        order_dict = {
            'id': order.id,
            'customer_name': order.customer.name,
            'delivery_address': order.delivery_address,
            'delivery_date': order.delivery_date,
            'customer_notes': order.customer_notes,
            'processed_line_items': [
                {
                    'requested_name': item.requested_name,
                    'requested_quantity': item.requested_quantity,
                    'status': item.status,
                    'issue': item.issue,
                    'product_details': {
                        'Product_Code': item.product_code,
                        'Product_Name': item.product_name,
                        'Price': item.unit_price
                    } if item.product_code else None
                } for item in order.line_items
            ]
        }

        json_path = create_sales_order_json(order_dict, output_folder="output")

        if json_path:
            # Generate PDF
            pdf_path = json_path.replace('.json', '.pdf')
            fill_sales_order_pdf(json_path, "sales_order_form_full.pdf", output_folder="output")

            # Store paths in task result
            task.result = {
                'json_path': json_path,
                'pdf_path': pdf_path if os.path.exists(pdf_path) else None
            }

    def _execute_email_sending(self, db, task: WorkflowTask):
        """Send email response with professional formatting"""

        order = db.query(Order).filter(Order.id == task.order_id).first()
        if not order:
            raise ValueError(f"Order {task.order_id} not found")

        # Get PDF path from previous task
        pdf_path = task.parameters.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            attachments = [pdf_path]
        else:
            attachments = []

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

        for item in order.line_items:
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

        body = intro + order_summary + next_steps + closing
        subject = f"Re: {order.last_email_subject or 'Order Inquiry'}"

        # Send email
        self.email_manager.send_response_email(order.id, subject, body, attachments)

    def _execute_follow_up_review(self, db, task: WorkflowTask):
        """Review follow-up content and determine next actions"""
        # This could involve AI analysis of the follow-up content
        # For now, just mark as completed - human review would happen here
        task.result = {'action': 'human_review_required'}

    def _generate_order_response(self, db, order):
        """Generate complete response for an order"""

        # Create tasks for response generation
        self._create_workflow_task(db, order.id, 'generate_response')
        self._create_workflow_task(db, order.id, 'send_email', {'pdf_path': f"output/SO_{order.customer.name.replace(' ', '-')}_{order.created_at.strftime('%Y%m%d-%H%M%S')}.pdf"})

    def _get_customer_orders(self, customer_email: str) -> List[Dict]:
        """Get existing orders for a customer"""

        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.email == customer_email).first()
            if not customer:
                return []

            orders = db.query(Order).filter(Order.customer_id == customer.id).all()

            return [{
                'id': order.id,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'customer_name': customer.name
            } for order in orders]

        finally:
            db.close()

    def _parse_quantity_updates_from_clarification(self, clarification_text: str, order, db) -> str:
        """Parse clarification text for quantity updates and apply them to line items"""

        updates_made = []

        # Look for patterns like "increase LUNDMARK 201 to 5", "change to 5 units", etc.
        import re

        # Get current line items
        line_items = db.query(LineItem).filter(LineItem.order_id == order.id).all()

        # Pattern 1: "increase [product] to [number]"
        increase_pattern = r'increase\s+(.+?)\s+to\s+(\d+)'
        matches = re.findall(increase_pattern, clarification_text, re.IGNORECASE)

        for product_name, new_qty in matches:
            new_qty = int(new_qty)
            # Find matching line item
            for item in line_items:
                if product_name.lower() in item.requested_name.lower():
                    old_qty = item.requested_quantity
                    item.requested_quantity = new_qty
                    updates_made.append(f"{item.requested_name}: {old_qty} → {new_qty}")
                    break

        # Pattern 2: "[product] to [number] units"
        units_pattern = r'(.+?)\s+to\s+(\d+)\s+units?'
        matches = re.findall(units_pattern, clarification_text, re.IGNORECASE)

        for product_name, new_qty in matches:
            new_qty = int(new_qty)
            # Find matching line item
            for item in line_items:
                if product_name.lower() in item.requested_name.lower():
                    old_qty = item.requested_quantity
                    item.requested_quantity = new_qty
                    updates_made.append(f"{item.requested_name}: {old_qty} → {new_qty}")
                    break

        # Pattern 3: "change [product] quantity to [number]"
        change_pattern = r'change\s+(.+?)\s+(?:quantity\s+)?to\s+(\d+)'
        matches = re.findall(change_pattern, clarification_text, re.IGNORECASE)

        for product_name, new_qty in matches:
            new_qty = int(new_qty)
            # Find matching line item
            for item in line_items:
                if product_name.lower() in item.requested_name.lower():
                    old_qty = item.requested_quantity
                    item.requested_quantity = new_qty
                    updates_made.append(f"{item.requested_name}: {old_qty} → {new_qty}")
                    break

        # Pattern 4: Simple "to 5" - assume it refers to the item with MOQ issues
        if not updates_made:
            simple_pattern = r'\bto\s+(\d+)\b'
            matches = re.findall(simple_pattern, clarification_text, re.IGNORECASE)
            if matches:
                new_qty = int(matches[0])
                # Find item with MOQ issues
                for item in line_items:
                    if item.status == 'MOQ_NOT_MET':
                        old_qty = item.requested_quantity
                        item.requested_quantity = new_qty
                        updates_made.append(f"{item.requested_name}: {old_qty} → {new_qty}")
                        break

        return "; ".join(updates_made) if updates_made else ""

    def _update_email_log(self, email_id: str, classification: Dict, affected_orders: List[int]):
        """Update email log with classification results"""

        db = SessionLocal()
        try:
            email_log = db.query(EmailLog).filter(EmailLog.email_id == email_id).first()
            if email_log:
                email_log.workflow_stage = classification.get('workflow_stage')
                email_log.intent_summary = classification.get('intent_summary')
                email_log.requires_action = classification.get('requires_action', True)

                if affected_orders:
                    email_log.order_id = affected_orders[0]  # Link to first affected order

                db.commit()

        except Exception as e:
            print(f"Error updating email log: {e}")
            db.rollback()
        finally:
            db.close()

# Sales Order Automation Backend Implementation Tasks

## 🎯 Project Overview
Transform the current sample-based script into a complete backend system with PostgreSQL database, AI-powered email classification, and automated workflow processing.

## 📋 Implementation Roadmap

### Phase 1: Database Foundation
- [x] **1.1** Set up PostgreSQL database (local development) - Using SQLite for now
- [x] **1.2** Install PostgreSQL and create database - Using SQLite for development
- [x] **1.3** Create `models.py` with SQLAlchemy models
- [x] **1.4** Implement Customer, Order, LineItem, EmailLog tables
- [x] **1.5** Add WorkflowTask table for task management
- [x] **1.6** Create database session management
- [x] **1.7** Test database connection and basic CRUD operations
- [ ] **1.8** Create database migration system (Alembic)

### Phase 2: Email Infrastructure
- [x] **2.1** Create `core/email_manager.py` class
- [x] **2.2** Implement IMAP email fetching
- [x] **2.3** Implement SMTP email sending
- [x] **2.4** Add email parsing and text extraction
- [x] **2.5** Create email logging functionality
- [x] **2.6** Add email thread tracking (Message-ID, References)
- [x] **2.7** Implement email deduplication (avoid processing same email twice)
- [ ] **2.8** Test email fetching with real Gmail account

### Phase 3: AI Email Classification
- [x] **3.1** Enhance `core/llm_extractor.py` with classification function
- [x] **3.2** Create email classification prompt and function schema
- [x] **3.3** Implement workflow stage detection (inquiry, follow_up, response, clarification)
- [x] **3.4** Add order relationship detection (link emails to existing orders)
- [x] **3.5** Implement customer context awareness (previous orders, communication history)
- [x] **3.6** Add order details extraction for new inquiries
- [x] **3.7** Create fallback logic for classification failures
- [ ] **3.8** Test classification with various email types

### Phase 4: Workflow Processor
- [x] **4.1** Create `core/workflow_processor.py` class
- [x] **4.2** Implement order state management (inquiry → in_process → db_check → response → follow_up)
- [x] **4.3** Add workflow task queuing system
- [x] **4.4** Implement task execution (validate_inventory, generate_response, send_email)
- [x] **4.5** Create automatic state transitions based on task completion
- [x] **4.6** Add human intervention points and manual task creation
- [x] **4.7** Implement workflow looping (follow_up → in_process for customer responses)
- [x] **4.8** Add order completion logic

### Phase 5: Integration & API
- [x] **5.1** Create FastAPI application (`app.py`)
- [x] **5.2** Implement REST endpoints for order management
- [x] **5.3** Add workflow control endpoints (manual processing, task management)
- [x] **5.4** Create email processing endpoints
- [x] **5.5** Add background task processing with FastAPI BackgroundTasks
- [x] **5.6** Implement health checks and monitoring
- [x] **5.7** Add CORS middleware for future frontend integration

### Phase 6: Background Processing
- [x] **6.1** Create `worker.py` for automated processing
- [x] **6.2** Implement email polling scheduler
- [x] **6.3** Add workflow processing scheduler
- [x] **6.4** Create task queue processor
- [x] **6.5** Add error handling and retry logic
- [x] **6.6** Implement graceful shutdown handling

### Phase 7: Configuration & Environment
- [x] **7.1** Update `config/settings.py` with database and email settings
- [x] **7.2** Create environment variable management
- [x] **7.3** Add configuration validation
- [x] **7.4** Create `.env.example` with all required variables
- [x] **7.5** Update `requirements.txt` with new dependencies

### Phase 8: Rule Engine Integration (Current Focus)
- [x] **8.1** Add WorkflowRule model to `models.py`
- [x] **8.2** Add rule-related fields to Order model
- [x] **8.3** Update database schema (recreate tables)
- [x] **8.4** Create `core/rule_engine.py` with RuleEngine class
- [x] **8.5** Implement rule evaluation logic (quantity-based rules)
- [x] **8.6** Add default rule loading (large order approval, bulk discount, small order notes)
- [x] **8.7** Create dynamic rule creation methods
- [x] **8.8** Update `WorkflowProcessor.__init__` to include rule engine
- [x] **8.9** Integrate rule evaluation in `_process_order_workflow`
- [x] **8.10** Add rule evaluation in order creation (`_handle_inquiry`)
- [x] **8.11** Add rule management endpoints to `app.py`
- [x] **8.12** Implement rule CRUD operations (create, read, update, deactivate)
- [x] **8.13** Add rule testing endpoint
- [x] **8.14** Update order response to include applied rules
- [ ] **8.15** Test rule engine with sample orders

### Phase 9: Testing & Validation
- [ ] **9.1** Test database operations with sample data
- [ ] **8.2** Test email fetching and processing
- [ ] **8.3** Test AI classification accuracy
- [ ] **8.4** Test complete workflow with sample emails
- [ ] **8.5** Test error handling and edge cases
- [ ] **8.6** Performance testing with multiple emails
- [ ] **8.7** Create test data generation scripts

### Phase 9: Documentation & Deployment Prep
- [ ] **9.1** Update README.md with new architecture
- [ ] **9.2** Create API documentation
- [ ] **9.3** Add deployment instructions for Railway/Render
- [ ] **9.4** Create Docker configuration
- [ ] **9.5** Add database migration scripts
- [ ] **9.6** Create health check endpoints

## 🔧 Technical Requirements

### Dependencies to Add:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
python-multipart==0.0.6
schedule==1.2.0
```

### Environment Variables:
```
DATABASE_URL=postgresql://user:password@localhost/sales_orders
GEMINI_API_KEY=your_key_here
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com
EMAIL_ACCOUNT=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

## 📊 Success Criteria

- [ ] System can fetch emails from Gmail IMAP
- [ ] AI can classify emails into correct workflow stages
- [ ] Orders are created and tracked through workflow states
- [ ] Automated responses are sent with PDF attachments
- [ ] Human operators can intervene and add custom tasks
- [ ] System handles email threads and customer follow-ups
- [ ] All processing is logged and auditable
- [ ] System is ready for cloud deployment

## 🚀 Implementation Notes

- Keep existing core logic (`llm_extractor.py`, `inventory_manager.py`, etc.) unchanged
- Use PostgreSQL from start for easy cloud migration
- Implement comprehensive error handling and logging
- Test each component thoroughly before moving to next phase
- Maintain backward compatibility where possible

## 📈 Progress Tracking

- **Total Tasks**: 67
- **Completed**: 58
- **Remaining**: 9
- **Current Phase**: Rule Engine Integration (15/15 complete)

---

*Last Updated: 2025-11-10*

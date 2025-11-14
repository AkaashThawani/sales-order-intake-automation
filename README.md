# Sales Order Intake Automation

## Links
- **Frontend Repository**: [https://github.com/AkaashThawani/sales-order-ui](https://github.com/AkaashThawani/sales-order-ui)
- **Backend Repository**: [https://github.com/AkaashThawani/sales-order-intake-automation](https://github.com/AkaashThawani/sales-order-intake-automation)
- **My GitHub**: [https://github.com/AkaashThawani](https://github.com/AkaashThawani)

## Description

This AI-powered Python application provides a complete backend system for automating sales order processing from emails. It features:

- **AI-powered email classification** and order extraction using Google Gemini
- **Intelligent product validation** against inventory catalogs
- **Business rule engine** for automated approval workflows
- **Automated PDF generation** for sales orders
- **Full REST API** with FastAPI
- **Database persistence** with SQLAlchemy
- **Background task processing** for workflow automation
- **Email thread management** and conversation tracking

## Architecture Overview

The system consists of two main components:

1. **Backend API** (`sales-order-intake-automation/`): FastAPI-based REST service
2. **Web UI** (`sales-order-ui/`): React/TypeScript frontend for order management

## Complete Workflow Overview

```
Customer Email → AI Classification → Order Creation (inquiry)
       ↓
Auto-advance → Inventory Validation → Business Rules → Approval Check
       ↓
Order Status: "in_process" → "db_check" → "response"/"follow_up"
       ↓
Customer Responds → Continue Conversation → Order Completion
       ↓
Order Status: "completed"
```

**Detailed Automated Flow:**
1. **Customer sends email** with order inquiry
2. **AI classifies email** → Determines workflow stage (inquiry/follow_up/response/clarification)
3. **Order creation/extraction** → AI extracts customer details, products, quantities
4. **Auto-advancement** → Order moves from "inquiry" to "in_process"
5. **Inventory validation** → Each product checked against catalog:
   - ✅ **VALIDATED**: Product exists, sufficient stock, meets MOQ
   - ❌ **NOT_FOUND**: Product not in catalog
   - ⚠️ **MOQ_NOT_MET**: Below minimum order quantity
   - 📦 **INSUFFICIENT_STOCK**: Not enough inventory
   - 🎯 **MULTIPLE_MATCHES**: Ambiguous product name
6. **Business rule evaluation** → Automated checks on validated items:
   - Large quantity approval (>50 items)
   - Bulk discount eligibility (>20 items)
   - Small order follow-up (<3 items)
   - High value review (>$1000)
7. **Approval workflow** → Human approval required for flagged orders
8. **Response generation** → AI creates professional email responses
9. **PDF generation** → Automated sales order PDF creation
10. **Email sending** → Professional responses with PDF attachments
11. **Conversation tracking** → Thread management for follow-ups
12. **Order completion** → Final status when customer confirms

## Key Features

- **AI-Powered Email Classification**: Automatically categorizes incoming emails into workflow stages:
  - **INQUIRY**: New order requests
  - **FOLLOW_UP**: Customer responses to previous communications
  - **RESPONSE**: Internal responses to customer inquiries
  - **CLARIFICATION**: Requests for additional information

- **Intelligent Order Extraction**: Uses Google Gemini to extract structured data from unstructured emails:
  - Customer information (name, email, address, delivery dates)
  - Product details (names, quantities, specifications)
  - Special instructions and notes

- **Advanced Product Validation**: Multi-tier validation system:
  - **Exact matching** against product catalog
  - **Fuzzy matching** for typos and variations
  - **Business rule validation** (MOQ, stock levels, pricing)
  - **Ambiguity detection** for unclear product references

- **Business Rule Engine**: Configurable rules for automated decision-making:
  - Quantity-based approvals (>50 items require approval)
  - Bulk discount eligibility (>20 items)
  - Small order follow-up (<3 items)
  - High-value order reviews (>$1000)

- **Automated Workflow Processing**: Background task system that:
  - Processes orders through validation stages
  - Generates professional email responses
  - Creates PDF sales order documents
  - Manages approval workflows

- **Full REST API**: Comprehensive endpoints for:
  - Order management (CRUD operations)
  - Email processing and conversation tracking
  - Workflow control and task management
  - Business rule configuration
  - PDF generation and file serving

- **Web Dashboard**: Complete React/TypeScript interface for:
  - Order monitoring and management
  - Email conversation views
  - Manual approval workflows
  - Business rule management
  - Real-time status updates

- **Database Persistence**: SQLAlchemy-based data model with:
  - Customer relationship management
  - Order lifecycle tracking
  - Email thread management
  - Workflow task queuing
  - Audit logging

## Project Structure

```
sales-order-intake-automation/
├── .env.example          # Template for environment variables
├── .gitignore            # Specifies files for Git to ignore
├── app.py                # Flask web application for API access
├── Dockerfile            # Docker configuration for containerized deployment
├── main.py               # Main script to run the full pipeline locally
├── README.md             # This file
├── render.yaml           # Render deployment configuration
├── requirements.txt      # Project dependencies
├── sales_order_form_full.pdf # The blank PDF form to be filled
├── sales_order_template.pdf  # Backup or alternative PDF template
├── worker.py             # Worker script for background processing
├── config/               # Configuration files
├── core/                 # Core business logic modules
├── data/                 # Product catalog and data files
├── output/               # Generated JSON and PDF outputs
└── test_data/            # Sample email data for testing

Core modules:
├── llm_extractor.py      # AI-powered extraction using Google Gemini
├── inventory_manager.py  # Loads and searches the product catalog
├── decision_engine.py    # Validates orders against business rules
├── output_generator.py   # Creates JSON output files
├── pdf_writer.py         # Fills PDF sales order forms
├── consolidation_checker.py # Checks for order consolidations
```

## Setup and Installation

1.  **Clone or Download the Repository**
    - Ensure all the project files are available.

2.  **Navigate to the Project Directory**
    ```bash
    cd sales-order-intake-automation
    ```

3.  **Create and Activate a Virtual Environment**
    - **Windows:**
      ```powershell
      py -m venv venv
      .\venv\Scripts\Activate.ps1
      ```
    - **macOS / Linux:**
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```

4.  **Install Dependencies**
    - With your virtual environment active, run:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set Up Environment Variables**
    - Copy the `.env.example` file to create your `.env`:
      ```bash
      cp .env.example .env
      ```
    - Open `.env` and add your Google Gemini API key:
      ```
      GEMINI_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE"
      ```

## API Endpoints

The FastAPI backend provides comprehensive REST endpoints:

### Core Endpoints
- `GET /health` - Health check
- `POST /api/process-email` - Process incoming emails
- `POST /api/process-workflow` - Trigger workflow processing

### Order Management
- `GET /api/orders` - List all orders
- `GET /api/orders/{id}` - Get specific order details
- `PUT /api/orders/{id}/status` - Update order status
- `GET /api/orders/{id}/emails` - Get email conversation for order
- `GET /api/orders/{id}/generate-pdf` - Generate PDF for order

### Email Management
- `GET /api/emails` - List email logs
- `GET /api/emails/conversations` - Get email conversations grouped by order
- `DELETE /api/emails/{id}` - Delete email log

### Business Rules
- `GET /api/rules` - List all business rules
- `POST /api/rules` - Create new rule
- `GET /api/rules/{id}` - Get specific rule
- `PUT /api/rules/{id}` - Update rule
- `DELETE /api/rules/{id}` - Deactivate rule
- `POST /api/rules/test` - Test rule against sample data

### Workflow Tasks
- `POST /api/orders/{id}/tasks` - Add workflow task

### Response Generation
- `POST /api/orders/{id}/generate-response` - Generate AI response
- `POST /api/orders/{id}/respond` - Send email response

## Database Configuration

### Local Development (SQLite)
- **Default**: Uses SQLite database (`sales_orders.db`)
- **Automatic**: Tables created on startup
- **File-based**: Simple for development and testing

### Production (PostgreSQL on Render)
- **Managed**: Render provides PostgreSQL database
- **Persistent**: Data survives container restarts
- **Backed up**: Automatic daily backups
- **Scalable**: Connection pooling built-in

### Database Migration
The application automatically creates all required tables:
- `customers` - Customer information
- `orders` - Order headers with workflow status
- `line_items` - Order line items with validation status
- `email_logs` - Email conversation tracking
- `workflow_tasks` - Background task management
- `workflow_rules` - Business rule definitions

## How to Run

### Local Development
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python app.py
   ```
   - API available at `http://localhost:8000`
   - Health check at `http://localhost:8000/health`
   - API docs at `http://localhost:8000/docs`

### Docker Development
```bash
# Build and run with Docker
docker-compose up --build

# Or manually
docker build -t sales-order-api .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key sales-order-api
```

### Production Deployment (Render)

#### Step 1: Create PostgreSQL Database
1. Go to [render.com](https://render.com)
2. Click **"New"** → **"PostgreSQL"**
3. Configure:
   - Name: `sales-order-db`
   - Plan: Starter ($7/month)
4. **Copy the Internal Database URL**

#### Step 2: Deploy Web Service
1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - Runtime: Docker
   - Branch: main
   - Root Directory: `./sales-order-intake-automation`
4. **Set Environment Variables:**
   - `DATABASE_URL`: Paste from PostgreSQL service
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `EMAIL_ACCOUNT`: Your email address
   - `EMAIL_PASSWORD`: Your app password
   - `ALLOWED_ORIGINS`: Your frontend URL

#### Step 3: Verify Deployment
```bash
# Test health endpoint
curl https://your-api-url.onrender.com/health

# Test API documentation
open https://your-api-url.onrender.com/docs
```

### Testing the System

#### Process a Test Email
```bash
curl -X POST "http://localhost:8000/api/process-email" \
  -H "Content-Type: application/json" \
  -d '{"email_content": "Hi, I need 5 coffee mugs and 10 notebooks", "order_id": null}'
```

#### View in Web UI
- **Dashboard**: http://localhost:5173
- **Orders**: http://localhost:5173/orders
- **API Docs**: http://localhost:8000/docs

### Legacy CLI Mode
```bash
# Run main.py for file-based processing
python main.py
# Outputs JSON and PDF files to output/ directory
```

## Future Improvements

- **Full Web UI**: Expand the existing Flask API into a complete web interface for uploading emails, processing orders, and viewing generated PDFs.
- **Database Integration**: Replace the `Product Catalog.csv` file with a proper database (like SQLite or PostgreSQL) for more robust inventory and order management.
- **Direct Email Integration**: Add a module to connect to an email inbox (via IMAP) to process new orders automatically as they arrive.

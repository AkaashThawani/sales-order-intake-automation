# Sales Order Intake Automation

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

## How to Run

### Backend API Server
1. **Start the FastAPI server:**
   ```bash
   cd sales-order-intake-automation
   python app.py
   ```
   The API will be available at `http://localhost:8000`

2. **Health check:** Visit `http://localhost:8000/health`

### Web UI (React Frontend)
1. **Install dependencies:**
   ```bash
   cd sales-order-ui
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```
   The UI will be available at `http://localhost:5173`

### Full System Setup
1. **Start Backend API** (Terminal 1):
   ```bash
   cd sales-order-intake-automation
   python app.py
   ```

2. **Start Web UI** (Terminal 2):
   ```bash
   cd sales-order-ui
   npm run dev
   ```

3. **Access the application:**
   - **Web Dashboard**: http://localhost:5173
   - **API Documentation**: http://localhost:8000/docs

### Testing the System
1. **Process a test email:**
   ```bash
   curl -X POST "http://localhost:8000/api/process-email" \
     -H "Content-Type: application/json" \
     -d '{"email_content": "Hi, I need 5 coffee mugs and 10 notebooks", "order_id": null}'
   ```

2. **View orders in web UI** at http://localhost:5173

3. **Check API documentation** at http://localhost:8000/docs for all endpoints

### Local CLI Execution (Legacy)
1. **Select Test Cases:** Open `main.py` and modify the `email_files_to_test` list.

2. **Execute the Script:**
   ```bash
   python main.py
   ```

3. **Check the Output:** JSON and PDF files in the `output/` directory.

### Deployment
The application includes configurations for containerized deployment:
- Use `Dockerfile` for Docker builds
- Use `render.yaml` for deployment on Render or similar platforms
- The web UI can be built with `npm run build` and served statically

## Future Improvements

- **Full Web UI**: Expand the existing Flask API into a complete web interface for uploading emails, processing orders, and viewing generated PDFs.
- **Database Integration**: Replace the `Product Catalog.csv` file with a proper database (like SQLite or PostgreSQL) for more robust inventory and order management.
- **Direct Email Integration**: Add a module to connect to an email inbox (via IMAP) to process new orders automatically as they arrive.

# Sales Order Intake Automation

# Description

This AI-powered Python application automates sales order processing from emails. It extracts order details using Google Gemini, validates against product catalogs and rules, and generates PDFs. Features modular design, Flask API, and deployment options.

## Key Features

- **AI-Powered Data Extraction**: Leverages Google Gemini to reliably extract key order details from raw email text, including customer name, address, delivery dates, product names, quantities, and general notes.
- **Intelligent Product Matching**: Uses a two-tiered search strategy. It first attempts a high-confidence exact match and then uses a fuzzy matching algorithm (`thefuzz`) as a fallback to handle typos and ambiguity.
- **Comprehensive Business Rule Validation**: Automatically checks each requested item against critical business rules:
  - **SKU Existence**: Flags items that are not found in the catalog.
  - **Ambiguity Check**: Flags requests that match multiple products, preventing incorrect orders.
  - **Minimum Order Quantity (MOQ)**: Flags items where the requested quantity is below the required MOQ.
  - **Inventory Availability**: Flags items that have insufficient stock.
- **Structured Data Output**: Generates a clean JSON file for each order, separating fully validated `line_items` from `issues_for_review` that require human attention.
- **Automated PDF Generation**: Takes the processed order data and automatically fills out a pre-defined PDF sales order template, creating a ready-to-use document. The PDF generation is cross-platform and works on Windows, macOS, and Linux.

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

## How to Run

### Local CLI Execution
1.  **Select Test Cases:** Open `main.py` and modify the `email_files_to_test` list at the bottom of the file to include the emails you want to process.

2.  **Execute the Script from the Terminal:**
    ```bash
    py main.py
    ```

3.  **Check the Output:** For each email processed, a JSON file and a filled-out PDF sales order will be generated in the `output/` directory.

### Web Service (Flask API)
1.  **Run the Flask Application:**
    ```bash
    py app.py
    ```
    The application will run on `http://0.0.0.0:5000` by default, or the port specified in the `PORT` environment variable.

2.  **Health Check:** Visit `http://localhost:5000/health` to verify the service is running.

### Deployment
The application includes configurations for containerized deployment:
- Use `Dockerfile` for Docker builds.
- Use `render.yaml` for deployment on Render or similar platforms.

## Future Improvements

- **Full Web UI**: Expand the existing Flask API into a complete web interface for uploading emails, processing orders, and viewing generated PDFs.
- **Database Integration**: Replace the `Product Catalog.csv` file with a proper database (like SQLite or PostgreSQL) for more robust inventory and order management.
- **Direct Email Integration**: Add a module to connect to an email inbox (via IMAP) to process new orders automatically as they arrive.

# AI-Powered Sales Order Intake Automation

This Python application provides an end-to-end solution for automating sales order intake from emails. It uses a Large Language Model (Google Gemini) to parse unstructured email text, validates the request against a product catalog and business rules, and automatically generates a filled-out PDF sales order form.

## Key Features

- **AI-Powered Data Extraction**: Leverages Google Gemini to reliably extract key order details from raw email text, including customer name, address, delivery dates, product names, quantities, and general notes.
- **Fuzzy Product Matching**: Intelligently matches customer requests (e.g., "small steel screws") to official product names in the catalog, handling minor typos and ambiguity.
- **Business Rule Validation**: Automatically checks each requested item against critical business rules like product existence, ambiguity (multiple matches), and Minimum Order Quantity (MOQ).
- **Order Consolidation**: Checks the new order's delivery address against a list of pending shipments to flag potential cost-saving consolidation opportunities.
- **Structured JSON Output**: Generates a clean JSON file for each order, separating validated `line_items` from `issues_for_review` that require human attention.
- **Automated PDF Generation**: Takes the validated order data and automatically fills out a pre-defined PDF sales order template, creating a ready-to-use document.

## Project Structure

```
Hackathon/
│
├── .env                  # For API keys and secrets (not committed)
├── .gitignore            # Specifies files for Git to ignore
├── requirements.txt      # Project dependencies
├── sales_order_template.pdf # The blank PDF form to be filled
├── README.md             # This file
│
├── data/
│   ├── inventory.csv     # Product catalog
│   └── pending_shipments.csv # List of unshipped orders
│
├── test_data/
│   └── email_samples.py  # A collection of test emails
│
├── core/
│   ├── llm_extractor.py      # Handles all interaction with the Gemini AI
│   ├── inventory_manager.py  # Manages loading and searching the product catalog
│   ├── decision_engine.py    # Applies business rules and validation
│   ├── consolidation_checker.py # Checks for order merging opportunities
│   ├── output_generator.py   # Creates the intermediate JSON output file
│   └── pdf_writer.py         # Fills the PDF sales order form
│
└── main.py               # Main script to run the full pipeline
```

## Setup and Installation

1.  **Get the Project Files**
    - Ensure all the project files are located inside a folder named `Hackathon`.

2.  **Navigate to the Project Directory**
    - Open your terminal and navigate into the project folder.
    ```bash
    cd path/to/your/Hackathon
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
    - In the `Hackathon` root directory, create a new file named `.env`.
    - Add your Google Gemini API key to this file:
      ```
      GEMINI_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE"
      ```

## How to Run

1.  **Select a Test Case:** Open `main.py` and change the `selected_email` variable at the bottom of the file to any key from `email_samples.py` (e.g., `"email_1"`, `"email_2"`).

2.  **Execute the Script from the Terminal:**
    ```bash
    py main.py
    ```

3.  **Check the Output:** A JSON file and a filled-out PDF sales order will be generated in the `output/` directory.

## Future Improvements

- **Web Interface**: Build a simple web UI using Flask or Streamlit to upload emails or paste text and see the generated PDF.
- **Database Integration**: Replace the CSV files with a proper database (like SQLite or PostgreSQL) for more robust inventory and order management.
- **Email Integration**: Add a module to connect directly to an email inbox (via IMAP) to process new orders automatically.
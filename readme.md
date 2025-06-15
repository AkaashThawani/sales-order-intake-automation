# AI-Powered Sales Order Intake Automation

This Python application provides an end-to-end solution for automating sales order intake from emails. It uses a Large Language Model (Google Gemini) to parse unstructured email text, validates the request against a product catalog and business rules, and automatically generates a filled-out PDF sales order form.

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
Hackathon/
│
├── .env                  # For API keys and secrets (not committed)
├── .gitignore            # Specifies files for Git to ignore
├── requirements.txt      # Project dependencies
├── sales_order_form_full.pdf # The blank PDF form to be filled
├── README.md             # This file
│
├── data/
│   └── Product Catalog.csv # Master product catalog
│
├── test_data/
│   ├── sample_email_1.txt
│   ├── sample_email_2.txt
│   └── ... (etc.)
│
├── core/
│   ├── llm_extractor.py      # Handles all interaction with the Gemini AI
│   ├── inventory_manager.py  # Manages loading and searching the product catalog
│   ├── decision_engine.py    # Applies business rules and validation
│   ├── output_generator.py   # Creates the intermediate JSON output file
│   └── pdf_writer.py         # Fills the PDF sales order form
│
└── main.py               # Main script to run the full pipeline
```

## Setup and Installation

1.  **Get the Project Files**
    - Ensure all the project files are located inside a folder named `Hackathon`.

2.  **Navigate to the Project Directory**
    - Open your terminal (e.g., PowerShell, Command Prompt) and navigate into the project folder.
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

1.  **Select Test Cases:** Open `main.py` and modify the `email_files_to_test` list at the bottom of the file to include the emails you want to process.

2.  **Execute the Script from the Terminal:**
    ```bash
    py main.py
    ```

3.  **Check the Output:** For each email processed, a JSON file and a filled-out PDF sales order will be generated in the `output/` directory.

## Future Improvements

- **Web Interface**: Build a simple web UI using Flask or Streamlit to upload emails or paste text and see the generated PDF in the browser.
- **Database Integration**: Replace the `Product Catalog.csv` file with a proper database (like SQLite or PostgreSQL) for more robust inventory and order management.
- **Direct Email Integration**: Add a module to connect to an email inbox (via IMAP) to process new orders automatically as they arrive.
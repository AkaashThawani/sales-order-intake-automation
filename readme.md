# AI-Powered Sales Order Intake

This Python application automates the process of handling sales orders received via email. It uses a Large Language Model (Google Gemini) to parse unstructured email text, extract key order details, validate them against a product catalog, and generate a structured JSON output file ready for the next step in a business workflow.

## Key Features

- **AI-Powered Data Extraction**: Leverages Google Gemini's Function Calling to reliably extract the following from raw email text:
  - Customer Name & Company
  - Delivery Address
  - Requested Delivery Date
  - Product Names & Quantities
  - General Customer Notes
- **Fuzzy Product Matching**: Uses the `thefuzz` library to intelligently match customer requests (e.g., "small steel screws") to official product names in the catalog, handling minor typos and ambiguity.
- **Business Rule Validation**: Automatically checks each requested item against critical business rules:
  - **Product Existence**: Flags items that are not found in the catalog.
  - **Ambiguity Check**: Flags requests that match multiple products, preventing incorrect orders.
  - **Minimum Order Quantity (MOQ)**: Flags items where the requested quantity is below the required MOQ.
- **Order Consolidation Suggestions**: Checks the new order's delivery address against a list of pending shipments to flag potential cost-saving consolidation opportunities.
- **Structured JSON Output**: Generates a clean, machine-readable JSON file for each order, separating validated `line_items` from `issues_for_review` that require human attention.

## Project Structure

```
logistics-ai-app/
│
├── .env                  # For API keys and secrets (not committed)
├── .gitignore            # Specifies files for Git to ignore
├── requirements.txt      # Project dependencies
├── sales_order_template.pdf # (For future PDF generation feature)
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
│   └── output_generator.py   # Creates the final JSON output file
│
└── main.py               # Main script to run the pipeline
```

## Setup and Installation

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd logistics-ai-app
    ```

2.  **Create and Activate a Virtual Environment**
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

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables**
    - Create a file named `.env` in the root directory.
    - Copy the contents of `.env.example` (if you have one) or add your API key directly:
      ```
      GEMINI_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE"
      ```

## How to Run

1.  **Select a Test Case:** Open `main.py` and change the `selected_email` variable at the bottom to any key from `email_samples.py` (e.g., `"email_1"`, `"email_2"`).

2.  **Execute the Script:**
    ```bash
    py main.py
    ```

3.  **Check the Output:** A new JSON file will be generated in the `output/` directory with the processed order details.

## Next Steps

- [ ] Implement the "Bonus Round" feature: a PDF Writing Agent to automatically fill a `sales_order_template.pdf` using the generated JSON data.
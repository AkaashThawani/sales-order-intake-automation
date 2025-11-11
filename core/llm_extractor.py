import google.generativeai as genai
from config import settings
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # type: ignore

# Define the NEW, more complex function tool for Gemini
log_sales_order_func = genai.protos.FunctionDeclaration(  # type: ignore
    name="log_sales_order",
    description="Extracts all customer order information from an email to create a sales order.",
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "customer_name": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="The name of the customer or company placing the order, e.g., 'Innovate LLC' or 'John Doe'."
            ),
            "delivery_address": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="The full delivery street address, including city, state, and zip code."
            ),
            "delivery_date": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="The requested delivery date, e.g., 'November 10th, 2023' or 'end of the month'."
            ),
            "customer_notes": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Any other important notes, comments, or context from the customer."
            ),
            "products": genai.protos.Schema(
                type=genai.protos.Type.ARRAY,
                items=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "product_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The name or description of the product requested."
                        ),
                        "quantity": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="The number of units requested. A dozen means 12."
                        )
                    },
                    required=["product_name", "quantity"]
                )
            )
        },
        required=["customer_name", "delivery_address", "products"]
    )
)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    tools=[log_sales_order_func]
)

SYSTEM_PROMPT = """
You are a world-class data entry agent. Your task is to meticulously read a customer email and extract information with extreme precision using the 'log_sales_order' function.

**CRITICAL PRODUCT EXTRACTION RULES:**

1. **Product Format**: Look for lines that start with "-" or bullet points containing quantities followed by product names.
2. **Quantity First**: The number at the beginning is ALWAYS the quantity.
3. **Product Name**: Everything after the quantity is the product name - extract it EXACTLY as written.

**EXAMPLES:**
- Email says: "- 25 Desk TRÄNHOLM 19"
  → product_name: "Desk TRÄNHOLM 19", quantity: 25

- Email says: "- 15 Desk NORDMARK 476"
  → product_name: "Desk NORDMARK 476", quantity: 15

- Email says: "- 10 Desk VIKTSTA 642"
  → product_name: "Desk VIKTSTA 642", quantity: 10

- Email says: "- 3 Coffee HEMNTORP 601"
  → product_name: "Coffee HEMNTORP 601", quantity: 3

**YOUR TASK:**
1. Read the entire email carefully.
2. Identify the customer's name from the signature.
3. Extract the full delivery address.
4. Extract the requested delivery date.
5. Find ALL product lines and extract: quantity (first number) + product_name (everything after).
6. You MUST call the 'log_sales_order' function with the extracted data.
"""

def extract_order_details_from_email(email_body: str):
    """Uses Gemini to extract a full sales order structure from an email."""
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: Gemini API Key is not set.")
        return None

    try:
        chat = model.start_chat(history=[
            {'role': 'user', 'parts': [SYSTEM_PROMPT]},
            {'role': 'model', 'parts': [
                "Understood. I will meticulously extract all required sales order fields and call the function."]}
        ])

        response = chat.send_message(email_body)

        function_call = response.candidates[0].content.parts[0].function_call
        if function_call and function_call.name == "log_sales_order":
            # The API returns a special dict-like object, convert it to a standard dict
            order_details = {}
            for key, value in function_call.args.items():
                # If the value is a 'RepeatedComposite' (like our 'products' list)...
                if type(value).__name__ == 'RepeatedComposite':
                    # ...convert it to a standard Python list of dictionaries.
                    order_details[key] = [dict(item) for item in value]
                else:
                    # Otherwise, just add the key-value pair as is.
                    order_details[key] = value

            return order_details
        else:
            print("LLM did not call the function. It might not have found a valid order.")
            return None

    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return None

# Email Classification Function
classify_email_func = genai.protos.FunctionDeclaration(  # type: ignore
    name="classify_email",
    description="Classify email intent and extract order context for workflow routing",
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "workflow_stage": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                enum=["INQUIRY", "FOLLOW_UP", "RESPONSE", "CLARIFICATION"],
                description="The workflow stage this email belongs to"
            ),
            "related_order_id": genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description="ID of existing order this email relates to (if applicable)"
            ),
            "intent_summary": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Brief summary of the email's intent and purpose"
            ),
            "requires_action": genai.protos.Schema(
                type=genai.protos.Type.BOOLEAN,
                description="Whether this email requires processing action"
            ),
            "confidence_score": genai.protos.Schema(
                type=genai.protos.Type.NUMBER,
                description="Confidence score for the classification (0-1)"
            ),
            "order_details": genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                description="Order details if this is a new inquiry",
                properties={
                    "customer_name": genai.protos.Schema(type=genai.protos.Type.STRING),
                    "customer_email": genai.protos.Schema(type=genai.protos.Type.STRING),
                    "products": genai.protos.Schema(
                        type=genai.protos.Type.ARRAY,
                        items=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "product_name": genai.protos.Schema(type=genai.protos.Type.STRING),
                                "quantity": genai.protos.Schema(type=genai.protos.Type.INTEGER)
                            }
                        )
                    ),
                    "delivery_address": genai.protos.Schema(type=genai.protos.Type.STRING),
                    "delivery_date": genai.protos.Schema(type=genai.protos.Type.STRING),
                    "notes": genai.protos.Schema(type=genai.protos.Type.STRING)
                }
            )
        },
        required=["workflow_stage", "intent_summary", "requires_action", "confidence_score"]
    )
)

classification_model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    tools=[classify_email_func]
)

EMAIL_CLASSIFICATION_PROMPT = """
You are an expert email classification system for an automated sales order processing platform. Your task is to analyze incoming customer emails and classify them into the appropriate workflow stage.

## WORKFLOW STAGES:

**INQUIRY**: New customer order requests, first-time orders, no previous communication about this specific order
- Examples: "I'd like to place an order for...", "Can you send me a quote for...", "Please order the following items..."

**FOLLOW_UP**: Customer following up on existing orders, asking for status updates, making changes to existing orders
- Examples: "What's the status of my order?", "Can you change the delivery date?", "I need to add more items to order #123"

**RESPONSE**: Customer responding to our previous email/communication (confirmation, clarification request, acceptance, etc.)
- Examples: "Yes, that looks good", "I need to change the address", "Thank you for the confirmation"

**CLARIFICATION**: Customer providing additional information or clarification about an ongoing order
- Examples: "The delivery address should be...", "I meant 5 units not 3", "Here's the correct product name..."

## CLASSIFICATION RULES:

1. **Check Customer History First**: Look at the existing orders from this customer to determine context
2. **Analyze Email Content**: Keywords, references to previous communications, order numbers
3. **Determine Intent**: Is this starting a new process or continuing an existing one?
4. **Extract Order Details**: Only for INQUIRY emails that contain new order information

## CONTEXT INFORMATION:
{context_info}

## EMAIL TO CLASSIFY:
Subject: {subject}
From: {sender}
Body: {body}

Classify this email and provide the appropriate workflow routing information.
"""

def classify_email_intent(email_subject: str, email_body: str, email_sender: str, existing_orders: list = None, customer_history: list = None):
    """Classify email intent and extract context for workflow routing"""

    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: Gemini API Key is not set.")
        return {
            "workflow_stage": "INQUIRY",
            "intent_summary": "Classification failed - API key not set",
            "requires_action": True,
            "confidence_score": 0.0
        }

    # Build context from existing orders and customer history
    context_parts = []

    if existing_orders:
        context_parts.append("EXISTING ORDERS FROM THIS CUSTOMER:")
        for order in existing_orders:
            context_parts.append(f"- Order #{order['id']}: Status '{order['status']}' - Created {order['created_at'][:10]}")

    if customer_history:
        context_parts.append("\nRECENT EMAIL HISTORY:")
        for email in customer_history[:5]:  # Last 5 emails
            context_parts.append(f"- {email['direction'].title()}: {email['subject']} ({email['received_at'][:10]}) - {email.get('workflow_stage', 'unknown')}")

    context_info = "\n".join(context_parts) if context_parts else "No previous context available."

    prompt = EMAIL_CLASSIFICATION_PROMPT.format(
        context_info=context_info,
        subject=email_subject,
        sender=email_sender,
        body=email_body
    )

    try:
        chat = classification_model.start_chat()
        response = chat.send_message(prompt)

        function_call = response.candidates[0].content.parts[0].function_call
        if function_call and function_call.name == "classify_email":
            # Convert the response to a standard dict
            classification = {}
            for key, value in function_call.args.items():
                if type(value).__name__ == 'RepeatedComposite':
                    # Handle arrays (like products list)
                    classification[key] = [dict(item) for item in value]
                else:
                    classification[key] = value

            # Ensure required fields are present
            if 'workflow_stage' not in classification:
                classification['workflow_stage'] = 'INQUIRY'
            if 'intent_summary' not in classification:
                classification['intent_summary'] = 'Classification completed'
            if 'requires_action' not in classification:
                classification['requires_action'] = True
            if 'confidence_score' not in classification:
                classification['confidence_score'] = 0.8

            return classification
        else:
            print("AI did not call the classification function. Using fallback.")
            return {
                "workflow_stage": "INQUIRY",
                "intent_summary": "AI classification failed, defaulting to inquiry",
                "requires_action": True,
                "confidence_score": 0.3
            }

    except Exception as e:
        print(f"Error during email classification: {e}")
        return {
            "workflow_stage": "INQUIRY",
            "intent_summary": f"Classification error: {str(e)}",
            "requires_action": True,
            "confidence_score": 0.0
        }

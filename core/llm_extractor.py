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
    print(f"🤖 AI Extraction called with email body (first 200 chars): {email_body[:200]}...")

    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: Gemini API Key is not set.")
        return None

    try:
        chat = model.start_chat(history=[
            {'role': 'user', 'parts': [SYSTEM_PROMPT]},
            {'role': 'model', 'parts': [
                "Understood. I will meticulously extract all required sales order fields and call the function."]}
        ])

        print("📤 Sending email to Gemini AI for extraction...")
        response = chat.send_message(email_body)
        print(f"📥 Received response from Gemini: {response}")

        function_call = response.candidates[0].content.parts[0].function_call
        print(f"🔍 Function call: {function_call}")

        if function_call and function_call.name == "log_sales_order":
            print("✅ AI called log_sales_order function")
            # The API returns a special dict-like object, convert it to a standard dict
            order_details = {}
            for key, value in function_call.args.items():
                print(f"   Processing key: {key}, value type: {type(value)}")
                # If the value is a 'RepeatedComposite' (like our 'products' list)...
                if type(value).__name__ == 'RepeatedComposite':
                    # ...convert it to a standard Python list of dictionaries.
                    order_details[key] = [dict(item) for item in value]
                    print(f"   Converted {key} to list: {order_details[key]}")
                else:
                    # Otherwise, just add the key-value pair as is.
                    order_details[key] = value
                    print(f"   Set {key} = {value}")

            print(f"🎯 Final extracted order details: {order_details}")
            return order_details
        else:
            print("❌ LLM did not call the log_sales_order function. It might not have found a valid order.")
            print(f"   Available parts: {response.candidates[0].content.parts if response.candidates else 'No candidates'}")
            return None

    except Exception as e:
        print(f"❌ An error occurred while calling the Gemini API: {e}")
        import traceback
        traceback.print_exc()
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
You are an expert email classification and extraction system for an automated sales order processing platform. Your task is to analyze incoming customer emails, classify them into the appropriate workflow stage, AND extract customer and order information from the email content.

## WORKFLOW STAGES:

**INQUIRY**: New customer order requests, first-time orders, no previous communication about this specific order
- Examples: "I'd like to place an order for...", "Can you send me a quote for...", "Please order the following items..."

**FOLLOW_UP**: Customer following up on existing orders, asking for status updates, making changes to existing orders
- Examples: "What's the status of my order?", "Can you change the delivery date?", "I need to add more items to order #123"

**RESPONSE**: Customer responding to our previous email/communication (confirmation, clarification request, acceptance, etc.)
- Examples: "Yes, that looks good", "I need to change the address", "Thank you for the confirmation"

**CLARIFICATION**: Customer providing additional information or clarification about an ongoing order
- Examples: "The delivery address should be...", "I meant 5 units not 3", "Here's the correct product name..."

## EXTRACTION REQUIREMENTS:

For **INQUIRY** emails, you MUST extract order details including:
- **customer_name**: Extract from email signature (e.g., "Best regards, John Smith" → "John Smith")
- **customer_email**: Extract from email content if present, otherwise use the From address
- **products**: Extract product lines with quantities (e.g., "- 25 Desk TRÄNHOLM 19" → product_name: "Desk TRÄNHOLM 19", quantity: 25)
- **delivery_address**: Extract full delivery address if mentioned
- **delivery_date**: Extract requested delivery date if mentioned
- **notes**: Any additional customer notes or requirements

## CLASSIFICATION RULES:

1. **Check Customer History First**: Look at the existing orders from this customer to determine context
2. **Analyze Email Content**: Keywords, references to previous communications, order numbers
3. **Determine Intent**: Is this starting a new process or continuing an existing one?
4. **Extract Order Details**: For INQUIRY emails, ALWAYS populate the order_details field with extracted information

## CONTEXT INFORMATION:
{context_info}

## EMAIL TO CLASSIFY AND EXTRACT:
Subject: {subject}
From: {sender}
Body: {body}

Classify this email AND extract all available customer and order information. For INQUIRY emails, populate the order_details field completely.
"""

def classify_email_intent(email_subject: str, email_body: str, email_sender: str, existing_orders: list = None, customer_history: list = None, order_context: dict = None):
    """Classify email intent and extract context for workflow routing"""

    print(f"🧠 Classification called for email: '{email_subject}' from {email_sender}")
    print(f"📧 Email body (first 200 chars): {email_body[:200]}...")

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

    # Add specific order context if provided
    if order_context:
        context_parts.append(f"\nSPECIFIC ORDER CONTEXT (Order #{order_context['order_id']}):")
        context_parts.append(f"- Current Status: {order_context['order_status']}")
        context_parts.append("- Line Items:")
        for item in order_context['line_items']:
            issue_text = f" (Issue: {item['issue']})" if item['issue'] else ""
            context_parts.append(f"  * {item['name']}: {item['quantity']} units - Status: {item['status']}{issue_text}")
        context_parts.append("- Recent Email Thread:")
        for email in order_context['recent_emails'][:3]:
            context_parts.append(f"  * {email['direction']}: {email['subject']} - {email['workflow_stage']}")

    context_info = "\n".join(context_parts) if context_parts else "No previous context available."
    print(f"📋 Context info: {context_info[:300]}...")

    prompt = EMAIL_CLASSIFICATION_PROMPT.format(
        context_info=context_info,
        subject=email_subject,
        sender=email_sender,
        body=email_body
    )

    try:
        print("🤖 Sending email to classification AI...")
        chat = classification_model.start_chat()
        response = chat.send_message(prompt)
        print(f"📥 Classification AI response received")

        function_call = response.candidates[0].content.parts[0].function_call
        print(f"🔍 Classification function call: {function_call}")

        if function_call and function_call.name == "classify_email":
            print("✅ AI called classify_email function")
            # Convert the response to a standard dict
            classification = {}
            for key, value in function_call.args.items():
                print(f"   Processing classification key: {key}")
                if type(value).__name__ == 'RepeatedComposite':
                    # Handle arrays (like products list)
                    classification[key] = [dict(item) for item in value]
                    print(f"   Converted {key} to list: {classification[key]}")
                else:
                    classification[key] = value
                    print(f"   Set {key} = {value}")

            # Ensure required fields are present
            if 'workflow_stage' not in classification:
                classification['workflow_stage'] = 'INQUIRY'
            if 'intent_summary' not in classification:
                classification['intent_summary'] = 'Classification completed'
            if 'requires_action' not in classification:
                classification['requires_action'] = True
            if 'confidence_score' not in classification:
                classification['confidence_score'] = 0.8

            print(f"🎯 Final classification result: {classification}")
            return classification
        else:
            print("❌ AI did not call the classify_email function. Using fallback.")
            print(f"   Available parts: {response.candidates[0].content.parts if response.candidates else 'No candidates'}")
            return {
                "workflow_stage": "INQUIRY",
                "intent_summary": "AI classification failed, defaulting to inquiry",
                "requires_action": True,
                "confidence_score": 0.3
            }

    except Exception as e:
        print(f"❌ Error during email classification: {e}")
        import traceback
        traceback.print_exc()
        return {
            "workflow_stage": "INQUIRY",
            "intent_summary": f"Classification error: {str(e)}",
            "requires_action": True,
            "confidence_score": 0.0
        }

# Response Generation Function
generate_response_func = genai.protos.FunctionDeclaration(  # type: ignore
    name="generate_response",
    description="Generate an intelligent, professional email response based on order status and conversation history",
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "subject": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Appropriate email subject line for the response"
            ),
            "body": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description="Complete, professional email response body with proper formatting and structure"
            ),
            "tone": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                enum=["professional", "friendly", "urgent", "clarification_needed"],
                description="The appropriate tone for this response"
            ),
            "next_steps": genai.protos.Schema(
                type=genai.protos.Type.ARRAY,
                items=genai.protos.Schema(type=genai.protos.Type.STRING),
                description="List of recommended next steps or actions"
            )
        },
        required=["subject", "body", "tone", "next_steps"]
    )
)

response_model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    tools=[generate_response_func]
)

RESPONSE_GENERATION_PROMPT = """
You are an expert customer service representative for ABC Coffee Company. Your task is to generate professional, intelligent email responses to customer inquiries about their orders.

## YOUR ROLE:
- Professional, helpful, and knowledgeable about coffee products
- Clear and concise communication
- Focus on customer satisfaction and smooth order processing
- Use appropriate tone based on context

## RESPONSE GUIDELINES:

### **Structure Every Response:**
1. **Personal Greeting**: Use customer's name if available
2. **Context Acknowledgment**: Reference the specific inquiry or clarification
3. **Order Status Summary**: Clear overview of confirmed vs. pending items
4. **Next Steps**: What happens next and any required actions
5. **Professional Closing**: Company signature and contact info

### **Tone Guidelines:**
- **Professional**: Standard business communication
- **Friendly**: Warm, approachable for regular customers
- **Urgent**: When issues need immediate attention
- **Clarification_Needed**: When more information is required

### **Content Rules:**
- Use bullet points and clear formatting
- Include specific product names and quantities
- Show pricing when items are confirmed
- Be transparent about any issues or delays
- End with clear call-to-action

### **CRITICAL: Signature Format**
- **EXACT FORMAT REQUIRED:**
  ```
  Best regards,
  Sales Team
  ABC Coffee Company
  ```
- Do NOT add extra titles like "Customer Service"
- Do NOT modify the signature format
- Always use exactly this 3-line signature

## ORDER DETAILS:
{order_details}

## CONVERSATION HISTORY:
{conversation_history}

## RESPONSE TYPE: {response_type}

**CRITICAL INSTRUCTION:** You MUST call the 'generate_response' function with your response data.

Generate a complete, professional email response that addresses the customer's current inquiry and provides clear next steps. Use the EXACT signature format specified above.
"""

def generate_response_suggestion(order_details: dict, conversation_history: list, response_type: str = "customer_response"):
    """Generate an intelligent email response suggestion using AI"""

    print(f"🤖 Generating AI response suggestion for order {order_details.get('id', 'unknown')}")

    if not os.getenv("GEMINI_API_KEY"):
        raise Exception("Gemini API Key is not set. Please set GEMINI_API_KEY environment variable.")

    try:
        # Format order details
        order_info = f"""
Order ID: {order_details.get('id', 'N/A')}
Status: {order_details.get('status', 'Unknown')}
Customer: {order_details.get('customer_name', 'Valued Customer')}
Email: {order_details.get('customer_email', 'N/A')}

Line Items:
"""

        for item in order_details.get('line_items', []):
            status_emoji = "✅" if item.get('status') == 'VALIDATED' else "⚠️" if item.get('status') == 'MOQ_NOT_MET' else "❓"
            order_info += f"{status_emoji} {item.get('name', 'Unknown')}: {item.get('quantity', 0)} × ${item.get('unit_price', '0')} = ${item.get('total_price', '0')}\n"
            if item.get('issue'):
                order_info += f"   Issue: {item['issue']}\n"

        # Format conversation history
        if conversation_history:
            history_text = "\nRecent Conversation:\n"
            for email in conversation_history[-5:]:  # Last 5 emails
                direction = "→" if email.get('direction') == 'outgoing' else "←"
                history_text += f"{direction} {email.get('subject', 'No subject')}: {email.get('body', '')[:100]}...\n"
        else:
            history_text = "\nNo previous conversation history.\n"

        prompt = RESPONSE_GENERATION_PROMPT.format(
            order_details=order_info,
            conversation_history=history_text,
            response_type=response_type
        )

        print("📤 Sending to AI for response generation...")
        chat = response_model.start_chat()
        response = chat.send_message(prompt)
        print("📥 AI response generation completed")

        function_call = response.candidates[0].content.parts[0].function_call
        print(f"🔍 Response generation function call: {function_call}")

        if function_call and function_call.name == "generate_response":
            print("✅ AI called generate_response function")
            # Convert to standard dict
            result = {}
            for key, value in function_call.args.items():
                if type(value).__name__ == 'RepeatedComposite':
                    result[key] = [str(item) for item in value]
                else:
                    result[key] = value

            print(f"🎯 Generated response: {result.get('subject', 'No subject')}")
            return result.get('body', 'Response generation failed')
        else:
            raise Exception("AI did not call the expected generate_response function")

    except Exception as e:
        print(f"❌ Error generating AI response: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"AI response generation failed: {str(e)}")

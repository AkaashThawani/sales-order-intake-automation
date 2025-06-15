import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore

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

**CRITICAL RULE:** For the 'product_name', you MUST extract the name EXACTLY as it appears in the email, including any numbers or codes attached to it. DO NOT try to simplify or clean the product name.

- If the email says "Bed TRÄNBERG 858", you MUST extract "Bed TRÄNBERG 858".
- If the email says "Dining FJÄRDAL 292", you MUST extract "Dining FJÄRDAL 292".

**YOUR TASK & OTHER RULES:**
1.  Read the entire email.
2.  Identify the customer's name.
3.  Extract the full delivery address.
4.  Extract the requested delivery date.
5.  Extract ALL requested products and their quantities precisely.
6.  You MUST call the 'log_sales_order' function with the extracted data.
"""

def extract_order_details_from_email(email_body: str):
    """Uses Gemini to extract a full sales order structure from an email."""
    if not settings.GEMINI_API_KEY:
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

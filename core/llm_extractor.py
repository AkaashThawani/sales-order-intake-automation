import generativeai as genai # type: ignore
from config import settings
# We no longer need to import DEFAULT_QUANTITIES

# Configure the Gemini API with your key from settings.py
genai.configure(api_key=settings.GEMINI_API_KEY)

# Define the function "tool" for Gemini to use for structured output
log_product_request_func = genai.protos.FunctionDeclaration(
    name="log_product_request",
    description="Extracts product and quantity information from an email text.",
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "products": genai.protos.Schema(
                type=genai.protos.Type.ARRAY,
                items=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "product_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The name of the product requested, e.g., 'Blue Widget' or 'Small Steel Screws'."
                        ),
                        "quantity": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="The number of units requested. ONLY include this if a specific number is mentioned."
                        )
                    },
                    # --- CHANGE HERE: 'quantity' is no longer required ---
                    required=["product_name"] 
                )
            )
        },
        required=["products"]
    )
)

# Create the generative model and tell it about our tool
model = genai.GenerativeModel(
    model_name='gemini-pro',
    tools=[log_product_request_func]
)

# --- CHANGE HERE: A much simpler system prompt ---
SYSTEM_PROMPT = """
You are a precise logistics assistant. Your task is to extract product names from an email.

RULES:
1.  Read the entire email. The most recent message is the most important.
2.  Extract the name of every product mentioned.
3.  ONLY include the 'quantity' if a specific number is clearly stated for that product.
4.  If no number is mentioned for a product, DO NOT guess or add a quantity.
"""

def extract_product_details_from_email(email_body: str):
    """Uses Gemini function calling to extract products and explicitly stated quantities."""
    if not settings.GEMINI_API_KEY:
        print("ERROR: Gemini API Key is not set in your .env file.")
        return []

    try:
        chat = model.start_chat(history=[
            {'role': 'user', 'parts': [SYSTEM_PROMPT]},
            {'role': 'model', 'parts': ["Understood. I will extract product names and only include quantities if they are explicitly mentioned as numbers."]}
        ])
        
        response = chat.send_message(email_body)
        
        function_call = response.candidates[0].content.parts[0].function_call
        if function_call and function_call.name == "log_product_request":
            args = function_call.args
            return [dict(product) for product in args.get("products", [])]
        else:
            print("LLM did not identify any products to extract.")
            return []
            
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return []
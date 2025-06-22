from flask import Flask
import os

# Your core modules can be imported directly
# from core.decision_engine import some_function

app = Flask(__name__)

@app.route('/')
def hello():
    return "Smart Order Intake Web Service (V2.0) is running!"

@app.route('/health')
def health_check():
    # Render uses this to check if your service is alive
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
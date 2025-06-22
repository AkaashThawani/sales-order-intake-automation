# Use an official lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching
COPY requirements.txt .

# Install system dependencies needed by some Python libraries (like PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Add any other system libraries if needed in the future
    && rm -rf /var/lib/apt/lists/*

# Install the Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire project's code into the container
# This includes your 'core', 'data', and other folders
COPY . .

# Expose the port that the Flask app will run on
EXPOSE 5000

# The default command to run the web server.
# This will be used by your 'web' service on Render.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
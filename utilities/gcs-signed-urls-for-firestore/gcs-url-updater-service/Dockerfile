# Use an official, lightweight Python 3.9 image as a base
FROM python:3.9-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Set the command to run the application using Gunicorn, a production-grade server.
# It will listen on the port provided by the PORT environment variable, which Cloud Run sets automatically.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app

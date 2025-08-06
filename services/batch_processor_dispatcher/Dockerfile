# Use a slim Python base image for smaller size and faster cold starts.
# Python 3.9 is chosen as it's a stable, widely supported version.
FROM python:3.9-slim-buster

# Set the working directory inside the container.
# All subsequent commands will be run from this directory.
WORKDIR /app

# Copy the requirements.txt file into the container.
# This separates the dependency layer, allowing Docker to cache it.
# If only code changes, it won't re-download dependencies.
COPY requirements.txt .

# Install Python dependencies.
# --no-cache-dir ensures that pip doesn't store downloaded packages,
# further reducing the image size.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container.
# This assumes your main script is named main.py and is in the same directory
# as the Dockerfile in your local development environment.
COPY main.py .

# Command to run the application.
# Cloud Run expects your service to listen for HTTP requests.
# The `main` function in your Python script is designed to be the entry point
# for HTTP requests from Pub/Sub push subscriptions.
CMD ["python", "batch_processor_dispatcher.py"]

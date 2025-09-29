
FROM python:3.12-slim

# Install system dependencies required to compile Python libraries like Pillow
RUN apt-get update && apt-get install -y \
    build-essential \
    libz-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app will run on
EXPOSE 8080

# Command to run the application using Gunicorn with an increased timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "5000", "main:app"]
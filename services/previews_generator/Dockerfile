# Use a slim Python base image for smaller size and faster cold starts.
# Python 3.9 is chosen as it's a stable, widely supported version.
FROM python:3.9-slim-buster

# Allow statements and log messages to immediately appear in the Cloud Run logs
ENV PYTHONUNBUFFERED True

# Set the working directory inside the container.
# All subsequent commands will be run from this directory.
WORKDIR /app

# Copy the requirements.txt file into the container.
# This path is relative to the build context, which is now the parent 'services' directory.
COPY previews_generator/requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the shared common code into the container.
COPY common/ /app/common/

# Copy the service-specific application file.
COPY previews_generator/previews_generator.py .

EXPOSE 8080
CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 previews_generator:app
# Use a Python base image with Alpine for smaller size
FROM python:3.9-slim-buster

# Set working directory in the container
WORKDIR /app

# Install system dependencies, including FFmpeg which avtools often depends on
# You may need to adapt this based on how avtools is distributed/built.
# This example uses apt for Debian/Ubuntu based images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install avtools (placeholder - you'll need to adapt this based on its actual installation method)
# This assumes avtools can be cloned and possibly built or moved to a PATH directory.
# For a production scenario, you might pre-compile avtools and add it.
RUN git clone https://github.com/GoogleCloudPlatform/vertex-ai-creative-studio.git /opt/vertex-ai-creative-studio \
    && cd /opt/vertex-ai-creative-studio/experiments/mcp-genmedia \
    # Add avtools build/install steps here if necessary.
    # Example: if avtools has a 'make install' target:
    # && make install \
    # For now, let's assume `avtools` binary is placed in /usr/local/bin or similar after build
    # Or, if `avtools` is a Python script, you might add it to PATH.
    # For demonstration, we'll just ensure the path to avtools is known.
    # If `avtools` is a single binary, you could COPY it.
    && ln -s /opt/vertex-ai-creative-studio/experiments/mcp-genmedia/avtools /usr/local/bin/avtools || true # Symlink or copy if avtools is directly available there

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY main.py .

# Expose the port (Cloud Run will use $PORT env var by default)
ENV PORT 8080

# Command to run the application (e.g., if using Flask/FastAPI or Cloud Functions Framework)
# For Cloud Functions, the entrypoint is typically a specific function (e.g., 'handle_http_trigger')
# The functions-framework will serve the specified function.
ENTRYPOINT ["functions-framework", "--target", "handle_http_trigger", "--port", "8080"]

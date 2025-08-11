#!/bin/bash

# This script automates the process of running 'artifact_publish.sh' for a predefined list of services.
export GCP_PROJECT_ID="fox-metadata-468100"
export GCP_REGION="us-central1"
export AR_REPO_NAME="media-pipeline-images"


# An array containing the names of the services.
services=(
    "summaries_generator"
    "batch_processor_dispatcher"
    "previews_generator"
    "transcription_generator"
)

# Loop through each service name in the 'services' array.
for service_name in "${services[@]}"; do
    echo "--- Starting publish process for service: $service_name ---"
    
    # Execute the artifact_publish.sh script with the current service name as an argument.
    # The leading "./" ensures the script is run from the current directory.
    sh artifact.sh "$service_name"
    
    # A separator to make the output easier to read.
    echo "--- Finished publishing for $service_name ---"
    echo ""
done

echo "All specified services have been processed."
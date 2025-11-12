#!/bin/bash

# GCS bucket to scan
BUCKET="gs://c7-nebula-foundry-input"

# Pub/Sub topic to publish to
TOPIC="central-ingestion-topic"

echo "_______________________"

# List all files in the bucket
gsutil ls "$BUCKET/*.mp4" | while read -r file_location; do
  echo "Processing file: $file_location"

  # Get the file name from the full path and remove the extension
  file_name_with_ext=$(basename "$file_location")
  file_name="${file_name_with_ext%.*}"

  # Generate a random number
  random_number=$RANDOM

  # Create the asset_id (e.g., my-video-12345)
  asset_id="${file_name}-${random_number}"

  # Construct the JSON message
  message=$(cat <<EOF
{
  "asset_id": "$asset_id",
  "file_name": "$file_name",
  "file_location": "$file_location",
  "content_type": "video/mp4",
  "file_category": "video"
}
EOF
)

  # Print the command
  echo "
  gcloud pubsub topics publish \"$TOPIC\" --message='$message'
  "

  # Publish the message
  echo gcloud pubsub topics publish "$TOPIC" --message="$message"

  echo "Published message for $file_name"
done

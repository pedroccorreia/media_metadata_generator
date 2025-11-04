#!/bin/bash

# --- 1. Check for required arguments ---
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Error: Missing arguments."
  echo ""
  echo "Usage:   $0 <FULL_INPUT_GCS_URI> <OUTPUT_GCS_FOLDER_URI>"
  echo "Example: $0 gs://my-bucket/movies/my_video.mp4 gs://my-bucket/movies/output/"
  exit 1
fi

# --- 2. Set variables ---
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1" # <-- EDIT THIS if your region is different

INPUT_URI="$1"
OUTPUT_URI="$2"

# --- 3. Generate dynamic names ---
# Get just the filename (e.g., "my_video.mp4")
INPUT_FILENAME=$(basename "$INPUT_URI")

# Get the name without extension (e.g., "my_video")
INPUT_BASENAME="${INPUT_FILENAME%.*}"

# Create the new dynamic output filename (e.g., "my_video-720p.mp4")
OUTPUT_FILENAME="${INPUT_BASENAME}-720p.mp4"

echo "Submitting job for:"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Input:   $INPUT_URI"
echo "  Output:  ${OUTPUT_URI}${OUTPUT_FILENAME}"
echo "-----------------------------------------------------"


# --- 4. Create a temporary job.json file ---
# This uses a "heredoc" to write the JSON config,
# injecting your BASH variables.
cat > job.json << EOF
{
  "inputUri": "$INPUT_URI",
  "outputUri": "$OUTPUT_URI",
  "config": {
    "elementaryStreams": [
      {
        "key": "video-stream0",
        "videoStream": {
          "h264": {
            "heightPixels": 720,
            "widthPixels": 1280,
            "bitrateBps": 4500000,
            "frameRate": 30
          }
        }
      },
      {
        "key": "audio-stream0",
        "audioStream": {
          "codec": "aac",
          "bitrateBps": 128000
        }
      }
    ],
    "muxStreams": [
      {
        "key": "720p-video",
        "container": "mp4",
        "elementaryStreams": [
          "video-stream0",
          "audio-stream0"
        ],
        "fileName": "$OUTPUT_FILENAME"
      }
    ]
  }
}
EOF

# --- 5. Submit the job using the REST API ---
# We use curl and send the job.json we just created.
# gcloud auth print-access-token securely provides authentication.
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @job.json \
  "https://transcoder.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/jobs"

# --- 6. Clean up the temporary file ---
rm job.json
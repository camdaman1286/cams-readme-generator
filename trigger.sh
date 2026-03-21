#!/bin/bash
# Usage: ./trigger.sh
# Prompts for a GitHub repo URL, runs the pipeline, and offers refinement loop.

set -e

BUCKET=$(terraform output -raw readme_bucket_name)

echo ""
echo "README Generator"
echo "-------------------"
echo "Enter a public GitHub repo URL:"
read -e REPO_URL

if [ -z "$REPO_URL" ]; then
  echo "No URL provided. Exiting."
  exit 1
fi

# Extract repo name from URL
REPO_NAME=$(echo "$REPO_URL" | sed 's|.*/||' | sed 's|\.git||')
OUTPUT_KEY="outputs/${REPO_NAME}/README.md"
FEEDBACK_KEY="inputs/feedback/${REPO_NAME}.txt"

# Encode URL: :// becomes ---, / becomes -
FILENAME=$(echo "$REPO_URL" | sed 's|://|---|g' | sed 's|/|-|g')

run_pipeline() {
  echo ""
  echo "Triggering pipeline for: $REPO_URL"

  # Delete existing output so idempotency check doesn't skip it
  aws s3 rm "s3://${BUCKET}/${OUTPUT_KEY}" 2>/dev/null || true

  # Upload trigger file
  touch "$FILENAME"
  aws s3 cp "$FILENAME" "s3://${BUCKET}/inputs/${FILENAME}" --quiet
  rm "$FILENAME"

  echo "Waiting for pipeline to complete..."

  # Poll S3 every 5 seconds until README appears (max 3 minutes)
  MAX_WAIT=36
  COUNT=0
  while [ $COUNT -lt $MAX_WAIT ]; do
    sleep 5
    COUNT=$((COUNT + 1))

    if aws s3 ls "s3://${BUCKET}/${OUTPUT_KEY}" > /dev/null 2>&1; then
      echo ""
      echo "README generated!"
      echo "=================================="
      aws s3 cp "s3://${BUCKET}/${OUTPUT_KEY}" -
      echo ""
      echo "=================================="
      echo "Saved to: s3://${BUCKET}/${OUTPUT_KEY}"
      return 0
    fi

    echo "   Still waiting... (${COUNT}/${MAX_WAIT})"
  done

  echo "Timed out after 3 minutes. Check CloudWatch logs for errors."
  exit 1
}

# Run the pipeline for the first time
run_pipeline

# Refinement loop
while true; do
  echo ""
  echo "Are you happy with this README? (yes/no)"
  read -e HAPPY

  if [ "$HAPPY" = "yes" ] || [ "$HAPPY" = "y" ]; then
    echo ""
    echo "Done. README saved to: s3://${BUCKET}/${OUTPUT_KEY}"
    break
  fi

  echo ""
  echo "What would you like to improve?"
  read -e FEEDBACK

  if [ -z "$FEEDBACK" ]; then
    echo "No feedback provided. Exiting."
    break
  fi

  # Upload feedback to S3 so the orchestrator can pick it up
  echo "$FEEDBACK" | aws s3 cp - "s3://${BUCKET}/${FEEDBACK_KEY}" --quiet
  echo ""
  echo "Feedback saved. Re-running pipeline..."

  run_pipeline
done

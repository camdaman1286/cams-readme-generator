#!/bin/bash
# Usage: ./trigger.sh <github_repo_url>
# Example: ./trigger.sh https://github.com/nicedoc/onlyrat

set -e

REPO_URL=$1
BUCKET=$(terraform output -raw readme_bucket_name)

if [ -z "$REPO_URL" ]; then
  echo "Usage: ./trigger.sh <github_repo_url>"
  exit 1
fi

# Encode URL: :// becomes ---, / becomes -
FILENAME=$(echo "$REPO_URL" | sed 's|://|---|g' | sed 's|/|-|g')

echo "Triggering README generation for: $REPO_URL"
echo "Bucket: $BUCKET"

touch "$FILENAME"
aws s3 cp "$FILENAME" "s3://${BUCKET}/inputs/${FILENAME}"
rm "$FILENAME"

echo "Done. Watch logs with:"
echo "aws logs tail /aws/lambda/cams-ReadmeGeneratorOrchestrator --follow"

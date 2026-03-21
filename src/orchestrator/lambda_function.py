# src/orchestrator/lambda_function.py
# Lightweight trigger - parses S3 event and starts the Step Functions state machine
import json
import boto3
import os
import urllib.parse
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

s3_client = boto3.client('s3')
sfn_client = boto3.client('stepfunctions')

STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")


def readme_exists(bucket, key):
    """Returns True if a README already exists at the given S3 path."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.ClientError:
        return False


def handler(event, context):
    """Parses S3 trigger event and starts the Step Functions state machine."""
    logger.info("Orchestrator triggered", extra={"event": json.dumps(event)})

    # 1. Parse repo URL from S3 event
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    filename = key.replace('inputs/', '')
    repo_url = filename.replace('---', '://', 1)
    parts = repo_url.split('://', 1)
    if len(parts) == 2:
        domain_and_path = parts[1].replace('-', '/', 2)
        repo_url = parts[0] + '://' + domain_and_path

    session_id = context.aws_request_id
    sanitized_repo_name = repo_url.split('/')[-1].replace('.git', '')
    output_key = f"outputs/{sanitized_repo_name}/README.md"
    feedback_key = f"inputs/feedback/{sanitized_repo_name}.txt"

    logger.info("Parsed request", extra={
        "repo_url": repo_url,
        "output_key": output_key
    })

    # 2. Idempotency check
    force = os.environ.get("FORCE_REGENERATE", "false").lower() == "true"
    if not force and readme_exists(OUTPUT_BUCKET, output_key):
        logger.info("README already exists, skipping", extra={"output_key": output_key})
        return {
            'statusCode': 200,
            'body': json.dumps(f"README already exists at {output_key}.")
        }

    # 3. Start Step Functions execution
    sfn_input = json.dumps({
        "repo_url": repo_url,
        "repo_name": sanitized_repo_name,
        "session_id": session_id,
        "output_key": output_key,
        "feedback_key": feedback_key
    })

    response = sfn_client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=sfn_input
    )

    logger.info("State machine started", extra={"execution_arn": response["executionArn"]})

    return {
        'statusCode': 200,
        'body': json.dumps(f"Pipeline started: {response['executionArn']}")
    }

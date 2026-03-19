# src/orchestrator/lambda_function.py
import json
import boto3
import os
import urllib.parse
import logging

# Structured logging setup - use INFO by default, configurable via env var
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

# Agent IDs and alias IDs from environment variables
REPO_SCANNER_AGENT_ID = os.environ.get("REPO_SCANNER_AGENT_ID")
REPO_SCANNER_AGENT_ALIAS_ID = os.environ.get("REPO_SCANNER_AGENT_ALIAS_ID")
PROJECT_SUMMARIZER_AGENT_ID = os.environ.get("PROJECT_SUMMARIZER_AGENT_ID")
PROJECT_SUMMARIZER_AGENT_ALIAS_ID = os.environ.get("PROJECT_SUMMARIZER_AGENT_ALIAS_ID")
INSTALLATION_GUIDE_AGENT_ID = os.environ.get("INSTALLATION_GUIDE_AGENT_ID")
INSTALLATION_GUIDE_AGENT_ALIAS_ID = os.environ.get("INSTALLATION_GUIDE_AGENT_ALIAS_ID")
USAGE_EXAMPLES_AGENT_ID = os.environ.get("USAGE_EXAMPLES_AGENT_ID")
USAGE_EXAMPLES_AGENT_ALIAS_ID = os.environ.get("USAGE_EXAMPLES_AGENT_ALIAS_ID")
FINAL_COMPILER_AGENT_ID = os.environ.get("FINAL_COMPILER_AGENT_ID")
FINAL_COMPILER_AGENT_ALIAS_ID = os.environ.get("FINAL_COMPILER_AGENT_ALIAS_ID")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")


def invoke_agent_helper(agent_id, alias_id, session_id, input_text):
    """Invokes a Bedrock agent and returns its final text response."""
    logger.info("Invoking agent", extra={"agent_id": agent_id})
    try:
        response = bedrock_agent_runtime_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=input_text
        )
        completion = ""
        for event in response.get("completion"):
            chunk = event["chunk"]
            completion += chunk["bytes"].decode()
        logger.info("Agent responded successfully", extra={"agent_id": agent_id})
        return completion
    except Exception as e:
        logger.error("Agent invocation failed", extra={"agent_id": agent_id, "error": str(e)})
        return f"Error processing this section: {e}"


def readme_exists(bucket, key):
    """Returns True if a README already exists at the given S3 path."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.ClientError:
        return False


def handler(event, context):
    """Main Lambda handler — orchestrates all agents in sequence."""
    logger.info("Orchestrator started", extra={"event": json.dumps(event)})

    # 1. Parse the repo URL from the S3 trigger event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    # Decode filename back to a URL
    # e.g. inputs/https---github.com-TruLie13-municipal-ai -> https://github.com/TruLie13/municipal-ai
    filename = key.replace('inputs/', '')
    repo_url = filename.replace('---', '://', 1)
    parts = repo_url.split('://', 1)
    if len(parts) == 2:
        domain_and_path = parts[1].replace('-', '/', 2)
        repo_url = parts[0] + '://' + domain_and_path

    session_id = context.aws_request_id
    sanitized_repo_name = repo_url.split('/')[-1].replace('.git', '')
    output_key = f"outputs/{sanitized_repo_name}/README.md"

    logger.info("Parsed request", extra={
        "repo_url": repo_url,
        "output_key": output_key,
        "session_id": session_id
    })

    # 2. Idempotency check - skip if README already exists unless FORCE_REGENERATE is set
    force = os.environ.get("FORCE_REGENERATE", "false").lower() == "true"
    if not force and readme_exists(OUTPUT_BUCKET, output_key):
        logger.info("README already exists, skipping generation", extra={"output_key": output_key})
        return {
            'statusCode': 200,
            'body': json.dumps(f"README already exists at {output_key}. Set FORCE_REGENERATE=true to override.")
        }

    # 3. Run agents in sequence
    logger.info("Starting agent pipeline")

    file_list_json = invoke_agent_helper(
        REPO_SCANNER_AGENT_ID, REPO_SCANNER_AGENT_ALIAS_ID, session_id, repo_url
    )
    project_summary = invoke_agent_helper(
        PROJECT_SUMMARIZER_AGENT_ID, PROJECT_SUMMARIZER_AGENT_ALIAS_ID, session_id, file_list_json
    )
    installation_guide = invoke_agent_helper(
        INSTALLATION_GUIDE_AGENT_ID, INSTALLATION_GUIDE_AGENT_ALIAS_ID, session_id, file_list_json
    )
    usage_examples = invoke_agent_helper(
        USAGE_EXAMPLES_AGENT_ID, USAGE_EXAMPLES_AGENT_ALIAS_ID, session_id, file_list_json
    )

    # 4. Bundle all outputs and send to the Final Compiler
    compiler_input = json.dumps({
        "repository_name": sanitized_repo_name,
        "project_summary": project_summary,
        "installation_guide": installation_guide,
        "usage_examples": usage_examples
    })

    readme_content = invoke_agent_helper(
        FINAL_COMPILER_AGENT_ID, FINAL_COMPILER_AGENT_ALIAS_ID, session_id, compiler_input
    )

    # 5. Save the final README.md to S3
    try:
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=readme_content,
            ContentType='text/markdown'
        )
        logger.info("README uploaded successfully", extra={"s3_path": f"s3://{OUTPUT_BUCKET}/{output_key}"})
    except Exception as e:
        logger.error("Failed to upload README", extra={"error": str(e)})
        raise e

    return {
        'statusCode': 200,
        'body': json.dumps('README.md generated successfully!')
    }

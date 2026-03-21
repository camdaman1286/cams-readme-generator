# src/invoke_repo_scanner/lambda_function.py
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

REPO_SCANNER_AGENT_ID = os.environ.get("REPO_SCANNER_AGENT_ID")
REPO_SCANNER_AGENT_ALIAS_ID = os.environ.get("REPO_SCANNER_AGENT_ALIAS_ID")


def handler(event, context):
    """Invokes the Repo Scanner agent and returns the file list."""
    repo_url = event["repo_url"]
    session_id = event["session_id"]

    logger.info("Invoking Repo Scanner", extra={"repo_url": repo_url})

    response = bedrock_agent_runtime_client.invoke_agent(
        agentId=REPO_SCANNER_AGENT_ID,
        agentAliasId=REPO_SCANNER_AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=repo_url
    )

    completion = ""
    for ev in response.get("completion"):
        completion += ev["chunk"]["bytes"].decode()

    logger.info("Repo Scanner completed successfully")

    return {
        "repo_url": repo_url,
        "repo_name": event["repo_name"],
        "session_id": session_id,
        "output_key": event["output_key"],
        "feedback_key": event["feedback_key"],
        "file_list": completion
    }

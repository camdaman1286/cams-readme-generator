# src/invoke_usage/lambda_function.py
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

USAGE_EXAMPLES_AGENT_ID = os.environ.get("USAGE_EXAMPLES_AGENT_ID")
USAGE_EXAMPLES_AGENT_ALIAS_ID = os.environ.get("USAGE_EXAMPLES_AGENT_ALIAS_ID")


def handler(event, context):
    """Invokes the Usage Examples agent and returns the usage section."""
    file_list = event["file_list"]
    session_id = event["session_id"]

    logger.info("Invoking Usage Examples")

    response = bedrock_agent_runtime_client.invoke_agent(
        agentId=USAGE_EXAMPLES_AGENT_ID,
        agentAliasId=USAGE_EXAMPLES_AGENT_ALIAS_ID,
        sessionId=session_id + "-usage",
        inputText=file_list
    )

    completion = ""
    for ev in response.get("completion"):
        completion += ev["chunk"]["bytes"].decode()

    logger.info("Usage Examples completed successfully")

    return {"usage_examples": completion}

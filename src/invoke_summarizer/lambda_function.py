# src/invoke_summarizer/lambda_function.py
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

PROJECT_SUMMARIZER_AGENT_ID = os.environ.get("PROJECT_SUMMARIZER_AGENT_ID")
PROJECT_SUMMARIZER_AGENT_ALIAS_ID = os.environ.get("PROJECT_SUMMARIZER_AGENT_ALIAS_ID")


def handler(event, context):
    """Invokes the Project Summarizer agent and returns the summary."""
    file_list = event["file_list"]
    session_id = event["session_id"]

    logger.info("Invoking Project Summarizer")

    response = bedrock_agent_runtime_client.invoke_agent(
        agentId=PROJECT_SUMMARIZER_AGENT_ID,
        agentAliasId=PROJECT_SUMMARIZER_AGENT_ALIAS_ID,
        sessionId=session_id + "-summarizer",
        inputText=file_list
    )

    completion = ""
    for ev in response.get("completion"):
        completion += ev["chunk"]["bytes"].decode()

    logger.info("Project Summarizer completed successfully")

    return {"project_summary": completion}

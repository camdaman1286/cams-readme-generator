# src/invoke_installation/lambda_function.py
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

INSTALLATION_GUIDE_AGENT_ID = os.environ.get("INSTALLATION_GUIDE_AGENT_ID")
INSTALLATION_GUIDE_AGENT_ALIAS_ID = os.environ.get("INSTALLATION_GUIDE_AGENT_ALIAS_ID")


def handler(event, context):
    """Invokes the Installation Guide agent and returns the installation section."""
    file_list = event["file_list"]
    session_id = event["session_id"]

    logger.info("Invoking Installation Guide")

    response = bedrock_agent_runtime_client.invoke_agent(
        agentId=INSTALLATION_GUIDE_AGENT_ID,
        agentAliasId=INSTALLATION_GUIDE_AGENT_ALIAS_ID,
        sessionId=session_id + "-installation",
        inputText=file_list
    )

    completion = ""
    for ev in response.get("completion"):
        completion += ev["chunk"]["bytes"].decode()

    logger.info("Installation Guide completed successfully")

    return {"installation_guide": completion}

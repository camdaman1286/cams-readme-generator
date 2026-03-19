# src/orchestrator/lambda_function.py
import json
import boto3
import os
import urllib.parse

# Initialize AWS clients
s3_client = boto3.client("s3")
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime")

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
    print(f"Invoking agent {agent_id}")
    try:
        response = bedrock_agent_runtime_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=input_text,
        )
        completion = ""
        for event in response.get("completion"):
            chunk = event["chunk"]
            completion += chunk["bytes"].decode()
        print(f"Agent {agent_id} response: {completion}")
        return completion
    except Exception as e:
        print(f"Error invoking agent {agent_id}: {e}")
        return f"Error processing this section: {e}"


def handler(event, context):
    """Main Lambda handler — orchestrates all agents in sequence."""
    print(f"Orchestrator started. Event: {json.dumps(event)}")

    # 1. Parse the repo URL from the S3 trigger event
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    # Decode filename back to a URL
    # e.g. inputs/https---github.com-TruLie13-municipal-ai -> https://github.com/TruLie13/municipal-ai
    filename = key.replace("inputs/", "")
    repo_url = filename.replace("---", "://", 1)
    parts = repo_url.split("://", 1)
    if len(parts) == 2:
        domain_and_path = parts[1].replace("-", "/", 2)
        repo_url = parts[0] + "://" + domain_and_path

    session_id = context.aws_request_id
    sanitized_repo_name = repo_url.split("/")[-1].replace(".git", "")
    output_key = f"outputs/{sanitized_repo_name}/README.md"

    print(f"Repo URL: {repo_url}")
    print(f"Output key: {output_key}")

    # 2. Run agents in sequence
    file_list_json = invoke_agent_helper(
        REPO_SCANNER_AGENT_ID, REPO_SCANNER_AGENT_ALIAS_ID, session_id, repo_url
    )
    project_summary = invoke_agent_helper(
        PROJECT_SUMMARIZER_AGENT_ID,
        PROJECT_SUMMARIZER_AGENT_ALIAS_ID,
        session_id,
        file_list_json,
    )
    installation_guide = invoke_agent_helper(
        INSTALLATION_GUIDE_AGENT_ID,
        INSTALLATION_GUIDE_AGENT_ALIAS_ID,
        session_id,
        file_list_json,
    )
    usage_examples = invoke_agent_helper(
        USAGE_EXAMPLES_AGENT_ID,
        USAGE_EXAMPLES_AGENT_ALIAS_ID,
        session_id,
        file_list_json,
    )

    # 3. Bundle all outputs and send to the Final Compiler
    compiler_input = json.dumps(
        {
            "repository_name": sanitized_repo_name,
            "project_summary": project_summary,
            "installation_guide": installation_guide,
            "usage_examples": usage_examples,
        }
    )

    readme_content = invoke_agent_helper(
        FINAL_COMPILER_AGENT_ID,
        FINAL_COMPILER_AGENT_ALIAS_ID,
        session_id,
        compiler_input,
    )

    # 4. Save the final README.md to S3
    try:
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=readme_content,
            ContentType="text/markdown",
        )
        print(f"Uploaded README to s3://{OUTPUT_BUCKET}/{output_key}")
    except Exception as e:
        print(f"Failed to upload README: {e}")
        raise e

    return {"statusCode": 200, "body": json.dumps("README.md generated successfully!")}

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


def scan_is_empty(file_list_response):
    """Returns True if the repo scanner response indicates no files were found."""
    if not file_list_response:
        return True
    lowered = file_list_response.lower()
    if '"files": []' in lowered or '"files":[]' in lowered:
        return True
    if file_list_response.count('\n') < 2 and not any(
        ext in file_list_response for ext in ['.py', '.js', '.ts', '.go', '.rb', '.java', '.md']
    ):
        return True
    return False


def clean_readme(content):
    """Strips any preamble before the first Markdown H1 header."""
    marker = content.find('# ')
    if marker == -1:
        logger.warning("No H1 header found in compiler output, returning raw content")
        return content
    cleaned = content[marker:]
    if len(cleaned) < len(content):
        logger.info("Stripped preamble from compiler output")
    return cleaned


def get_feedback(bucket, feedback_key):
    """Retrieves user feedback from S3 if it exists."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=feedback_key)
        feedback = response['Body'].read().decode('utf-8').strip()
        logger.info("Feedback found", extra={"feedback": feedback})
        return feedback
    except s3_client.exceptions.ClientError:
        return None


def write_not_found_readme(repo_name, repo_url, output_key):
    """Writes a friendly not-found README to S3 when a repo can't be scanned."""
    content = f"""# {repo_name}

Hmm, we couldn't find this repository.

We looked for `{repo_url}` but came up empty. Here are a few things to check:

- Is the repository public? Private repos can't be scanned.
- Does the URL look right? Double-check for any typos.
- Is the repository empty? There may be nothing to scan yet.

Give it another shot with a valid public GitHub repository and we'll get your README generated in no time.
"""
    try:
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=content,
            ContentType='text/markdown'
        )
        logger.info("Not-found README uploaded", extra={"output_key": output_key})
    except Exception as e:
        logger.error("Failed to upload not-found README", extra={"error": str(e)})
        raise e


def handler(event, context):
    """Main Lambda handler — orchestrates all agents in sequence."""
    logger.info("Orchestrator started", extra={"event": json.dumps(event)})

    # 1. Parse the repo URL from the S3 trigger event
    bucket = event['Records'][0]['s3']['bucket']['name']
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

    # 3. Scan the repo first
    logger.info("Starting agent pipeline")

    file_list_json = invoke_agent_helper(
        REPO_SCANNER_AGENT_ID, REPO_SCANNER_AGENT_ALIAS_ID, session_id, repo_url
    )

    # 4. Guard - stop pipeline if repo scan returned nothing
    if scan_is_empty(file_list_json):
        logger.warning("Repo scan returned no files", extra={
            "repo_url": repo_url,
            "scanner_response": file_list_json
        })
        write_not_found_readme(sanitized_repo_name, repo_url, output_key)
        return {
            'statusCode': 200,
            'body': json.dumps(f"Repo not found or empty. Not-found README written to {output_key}.")
        }

    # 5. Run remaining agents in sequence
    project_summary = invoke_agent_helper(
        PROJECT_SUMMARIZER_AGENT_ID, PROJECT_SUMMARIZER_AGENT_ALIAS_ID, session_id, file_list_json
    )
    installation_guide = invoke_agent_helper(
        INSTALLATION_GUIDE_AGENT_ID, INSTALLATION_GUIDE_AGENT_ALIAS_ID, session_id, file_list_json
    )
    usage_examples = invoke_agent_helper(
        USAGE_EXAMPLES_AGENT_ID, USAGE_EXAMPLES_AGENT_ALIAS_ID, session_id, file_list_json
    )

    # 6. Check for user feedback and include it in the compiler input if present
    feedback = get_feedback(OUTPUT_BUCKET, feedback_key)

    compiler_input = {
        "repository_name": sanitized_repo_name,
        "project_summary": project_summary,
        "installation_guide": installation_guide,
        "usage_examples": usage_examples
    }

    if feedback:
        compiler_input["user_feedback"] = feedback
        compiler_input["instruction"] = (
            "The user has reviewed a previous version of this README and provided feedback. "
            "Apply their feedback when assembling the final document: " + feedback
        )
        logger.info("Feedback injected into compiler input")

    # 7. Send to Final Compiler
    readme_content = invoke_agent_helper(
        FINAL_COMPILER_AGENT_ID, FINAL_COMPILER_AGENT_ALIAS_ID, session_id, json.dumps(compiler_input)
    )

    # 8. Clean the output - strip any preamble before the first H1 header
    readme_content = clean_readme(readme_content)

    # 9. Save the final README.md to S3
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

    # 10. Clean up feedback file after use
    if feedback:
        try:
            s3_client.delete_object(Bucket=OUTPUT_BUCKET, Key=feedback_key)
            logger.info("Feedback file cleaned up", extra={"feedback_key": feedback_key})
        except Exception as e:
            logger.warning("Could not delete feedback file", extra={"error": str(e)})

    return {
        'statusCode': 200,
        'body': json.dumps('README.md generated successfully!')
    }

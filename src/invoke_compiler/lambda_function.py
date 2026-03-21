# src/invoke_compiler/lambda_function.py
import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
s3_client = boto3.client('s3')

FINAL_COMPILER_AGENT_ID = os.environ.get("FINAL_COMPILER_AGENT_ID")
FINAL_COMPILER_AGENT_ALIAS_ID = os.environ.get("FINAL_COMPILER_AGENT_ALIAS_ID")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")


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


def handler(event, context):
    """Assembles all agent outputs and invokes the Final Compiler agent."""
    session_id = event["session_id"]
    repo_name = event["repo_name"]
    output_key = event["output_key"]
    feedback_key = event["feedback_key"]

    # Results come from the parallel state in Step Functions
    project_summary = event["project_summary"]
    installation_guide = event["installation_guide"]
    usage_examples = event["usage_examples"]

    logger.info("Invoking Final Compiler", extra={"repo_name": repo_name})

    # Check for user feedback
    feedback = get_feedback(OUTPUT_BUCKET, feedback_key)

    compiler_input = {
        "repository_name": repo_name,
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

    response = bedrock_agent_runtime_client.invoke_agent(
        agentId=FINAL_COMPILER_AGENT_ID,
        agentAliasId=FINAL_COMPILER_AGENT_ALIAS_ID,
        sessionId=session_id + "-compiler",
        inputText=json.dumps(compiler_input)
    )

    completion = ""
    for ev in response.get("completion"):
        completion += ev["chunk"]["bytes"].decode()

    # Clean output
    readme_content = clean_readme(completion)

    # Save to S3
    s3_client.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=output_key,
        Body=readme_content,
        ContentType='text/markdown'
    )
    logger.info("README uploaded successfully", extra={"output_key": output_key})

    # Clean up feedback file after use
    if feedback:
        try:
            s3_client.delete_object(Bucket=OUTPUT_BUCKET, Key=feedback_key)
            logger.info("Feedback file cleaned up")
        except Exception as e:
            logger.warning("Could not delete feedback file", extra={"error": str(e)})

    return {
        "statusCode": 200,
        "output_key": output_key,
        "body": "README.md generated successfully!"
    }

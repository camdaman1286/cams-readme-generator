import boto3
import sys
import subprocess
import json


def get_terraform_outputs():
    """Reads all relevant agent IDs from terraform output."""
    result = subprocess.run(
        ["terraform", "output", "-json"],
        capture_output=True,
        text=True
    )
    outputs = json.loads(result.stdout)
    return {
        "repo_scanner":       outputs["repo_scanner_agent_id"]["value"],
        "project_summarizer": outputs["project_summarizer_agent_id"]["value"],
        "installation_guide": outputs["installation_guide_agent_id"]["value"],
        "usage_examples":     outputs["usage_examples_agent_id"]["value"],
    }


def invoke_agent(client, agent_id, session_id, input_text, label):
    """Invokes a Bedrock agent and returns the response text."""
    print(f"\n[{label}] Invoking...")
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId='TSTALIASID',
        sessionId=session_id,
        inputText=input_text
    )
    completion = ""
    for event in response['completion']:
        if 'chunk' in event:
            completion += event['chunk']['bytes'].decode()
    print(f"[{label}] Done.")
    return completion


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_pipeline.py <github_repo_url>")
        print("Example: python3 test_pipeline.py https://github.com/TruLie13/municipal-ai")
        sys.exit(1)

    repo_url = sys.argv[1]

    print("Fetching agent IDs from Terraform outputs...")
    agents = get_terraform_outputs()

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    # Use repo name as session ID to keep agent contexts separate
    session_id = repo_url.split('/')[-1]

    print(f"\nStarting pipeline for: {repo_url}")
    print("=" * 60)

    # Step 1 — Scan the repo
    file_list = invoke_agent(
        client, agents["repo_scanner"], session_id, repo_url, "Repo Scanner"
    )

    # Step 2 — Run analytical agents against the file list
    project_summary = invoke_agent(
        client, agents["project_summarizer"], session_id, file_list, "Project Summarizer"
    )

    installation_guide = invoke_agent(
        client, agents["installation_guide"], session_id, file_list, "Installation Guide"
    )

    usage_examples = invoke_agent(
        client, agents["usage_examples"], session_id, file_list, "Usage Examples"
    )

    # Step 3 — Print the assembled output
    repo_name = repo_url.split('/')[-1]
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE — Generated README preview:")
    print("=" * 60)
    print(f"\n# {repo_name}\n")
    print("## Project Summary\n")
    print(project_summary)
    print(installation_guide)
    print(usage_examples)


if __name__ == "__main__":
    main()

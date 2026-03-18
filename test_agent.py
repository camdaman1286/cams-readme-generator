import boto3
import sys
import subprocess
import json


def get_terraform_output(key):
    """Reads a value from terraform output."""
    result = subprocess.run(
        ["terraform", "output", "-json"],
        capture_output=True,
        text=True
    )
    outputs = json.loads(result.stdout)
    return outputs[key]["value"]


AGENT_ALIASES = {
    "repo_scanner":        ("repo_scanner_agent_id",        "Repo Scanner"),
    "project_summarizer":  ("project_summarizer_agent_id",  "Project Summarizer"),
    "installation_guide":  ("installation_guide_agent_id",  "Installation Guide"),
    "usage_examples":      ("usage_examples_agent_id",      "Usage Examples"),
}

def print_usage():
    print("Usage: python3 test_agent.py <agent_name> <input_text>")
    print("")
    print("Available agents:")
    for name, (_, label) in AGENT_ALIASES.items():
        print(f"  {name:<25} ({label})")
    print("")
    print("Example:")
    print('  python3 test_agent.py repo_scanner https://github.com/TruLie13/municipal-ai')
    print('  python3 test_agent.py project_summarizer \'{"files": ["main.py", "requirements.txt"]}\'')


def main():
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    agent_name = sys.argv[1]
    input_text = sys.argv[2]

    if agent_name not in AGENT_ALIASES:
        print(f"Error: unknown agent '{agent_name}'")
        print("")
        print_usage()
        sys.exit(1)

    output_key, label = AGENT_ALIASES[agent_name]

    print(f"Fetching agent ID from Terraform outputs...")
    agent_id = get_terraform_output(output_key)
    print(f"Agent: {label} ({agent_id})")
    print(f"Input: {input_text}")
    print("-" * 50)

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId='TSTALIASID',
        sessionId='test-session-001',
        inputText=input_text
    )

    completion = ""
    for event in response['completion']:
        if 'chunk' in event:
            completion += event['chunk']['bytes'].decode()

    print(completion)


if __name__ == "__main__":
    main()

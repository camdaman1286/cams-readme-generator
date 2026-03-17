import boto3
import sys

if len(sys.argv) < 2:
    print("Usage: python3 test_agent.py <github_repo_url>")
    print("Example: python3 test_agent.py https://github.com/TruLie13/municipal-ai")
    sys.exit(1)

repo_url = sys.argv[1]

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

print(f"Invoking agent with repo: {repo_url}")
print("-" * 50)

response = client.invoke_agent(
    agentId='4PDUPHOPUZ',
    agentAliasId='TSTALIASID',
    sessionId='test-session-001',
    inputText=repo_url
)

completion = ""
for event in response['completion']:
    if 'chunk' in event:
        completion += event['chunk']['bytes'].decode()

print(completion)

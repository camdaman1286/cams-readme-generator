import boto3
import sys

if len(sys.argv) < 3:
    print("Usage: python3 test_agent.py <agent_id> <input_text>")
    print("Example: python3 test_agent.py JTMVPJX2M2 'files: main.py, requirements.txt'")
    sys.exit(1)

agent_id = sys.argv[1]
input_text = sys.argv[2]

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

print(f"Invoking agent {agent_id} with input:")
print(f"{input_text}")
print("-" * 50)

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

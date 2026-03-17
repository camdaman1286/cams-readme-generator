import json
import os
import subprocess
import shutil


def list_files_in_repo(repo_url):
    """Clones a git repo and returns a list of its files."""
    repo_dir = "/tmp/repo"

    # Clean up any previous clone
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    try:
        print(f"Cloning repository: {repo_url}")
        subprocess.run(
            ["git", "clone", repo_url, repo_dir],
            check=True,
            capture_output=True,
            text=True
        )
        print("Repository cloned successfully.")

        file_list = []
        for root, dirs, files in os.walk(repo_dir):
            # Skip the .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            for name in files:
                relative_path = os.path.relpath(os.path.join(root, name), repo_dir)
                file_list.append(relative_path)

        return {"files": file_list}

    except subprocess.CalledProcessError as e:
        print(f"Git clone failed: {e.stderr}")
        return {"files": []}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"files": []}


def handler(event, context):
    """Main Lambda handler. Parses Bedrock Agent input and returns file list."""
    print(f"Event received: {json.dumps(event)}")

    repo_url = None
    try:
        # Navigate the Bedrock Agent event structure to find repo_url
        properties = event['requestBody']['content']['application/json']['properties']
        repo_url = next((p['value'] for p in properties if p['name'] == 'repo_url'), None)
    except (KeyError, StopIteration):
        print("Error: Could not find repo_url in event.")

    if not repo_url:
        result = {"files": []}
    else:
        result = list_files_in_repo(repo_url)

    # Bedrock Agent requires this exact response structure
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event['actionGroup'],
            'apiPath': event['apiPath'],
            'httpMethod': event['httpMethod'],
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(result)
                }
            }
        }
    }

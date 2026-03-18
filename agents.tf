# The Repo Scanner Agent - uses a Lambda tool to clone and list repo files
module "repo_scanner_agent" {
  source                  = "./modules/bedrock_agent"
  agent_name              = "cams-Repo_Scanner_Agent"
  agent_resource_role_arn = module.bedrock_agent_role.role_arn
  instruction             = "Your job is to use the scan_repo tool to get a file list from a public GitHub URL. You are a helpful AI assistant. When a user provides a GitHub URL, you must use the available tool to scan it."
}

# Connects the agent to its Lambda tool via an OpenAPI schema
resource "aws_bedrockagent_agent_action_group" "repo_scanner_action_group" {
  agent_id           = module.repo_scanner_agent.agent_id
  agent_version      = "DRAFT"
  action_group_name  = "ScanRepoAction"
  action_group_state = "ENABLED"

  action_group_executor {
    lambda = aws_lambda_function.repo_scanner_lambda.arn
  }

  api_schema {
    payload = file("${path.root}/repo_scanner_schema.json")
  }
}

# Grants Bedrock permission to invoke the Lambda - scoped to this agent only
resource "aws_lambda_permission" "allow_bedrock_to_invoke_repo_scanner" {
  statement_id  = "AllowBedrockToInvokeRepoScannerLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.repo_scanner_lambda.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = module.repo_scanner_agent.agent_arn
}

# Analyzes file list and writes a concise project summary paragraph
module "project_summarizer_agent" {
  source                  = "./modules/bedrock_agent"
  agent_name              = "cams-Project_Summarizer_Agent"
  agent_resource_role_arn = module.bedrock_agent_role.role_arn
  instruction             = <<-EOT
    You are an expert software developer writing a project summary for a README.md.
    Analyze the provided file list and write a confident, factual summary of the project's purpose and key components.
    Do not use uncertain or hedging language like 'it appears to be', 'likely', or 'seems to be'. State your analysis as fact.
    Your response must be only the summary paragraph, nothing else.
  EOT
}

# Scans for dependency files and writes the installation section
module "installation_guide_agent" {
  source                  = "./modules/bedrock_agent"
  agent_name              = "cams-Installation_Guide_Agent"
  agent_resource_role_arn = module.bedrock_agent_role.role_arn
  instruction             = <<-EOT
    You are a technical writer creating a README.md. Your ONLY job is to scan the provided list of filenames.
    If you see a common dependency file, write a '## Installation' section in Markdown.
    Your response must be concise and contain ONLY the Markdown section with the install command in a bash code block.
    For example, if you see 'requirements.txt', your entire response MUST be:
    ## Installation
```bash
    pip install -r requirements.txt
```
    If you do not see any recognizable dependency files, respond with an empty string.
  EOT
}

# Identifies the main entry point and writes the usage section
module "usage_examples_agent" {
  source                  = "./modules/bedrock_agent"
  agent_name              = "cams-Usage_Examples_Agent"
  agent_resource_role_arn = module.bedrock_agent_role.role_arn
  instruction             = <<-EOT
    You are a software developer writing a README.md. Your ONLY task is to identify the most likely entry point from a list of filenames.
    Write a '## Usage' section in Markdown showing the command to run the project.
    Your response MUST be concise and wrap the command in a bash code block.
    For example, if you see 'main.py', your entire response MUST be:
    ## Usage
```bash
    python main.py
```
  EOT
}

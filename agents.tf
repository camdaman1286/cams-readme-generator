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

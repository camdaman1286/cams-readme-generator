# Role for Lambda functions to execute and write logs
module "lambda_execution_role" {
  source             = "./modules/iam"
  role_name          = "cams-ReadmeGeneratorLambdaExecutionRole"
  service_principals = ["lambda.amazonaws.com"]
  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

# Role for Bedrock Agents to invoke models
module "bedrock_agent_role" {
  source             = "./modules/iam"
  role_name          = "cams-ReadmeGeneratorBedrockAgentRole"
  service_principals = ["bedrock.amazonaws.com"]
  policy_arns = [
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
  ]
}

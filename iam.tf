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

# Dedicated role for the Orchestrator Lambda - separate from the basic Lambda role
module "orchestrator_execution_role" {
  source             = "./modules/iam"
  role_name          = "cams-ReadmeGeneratorOrchestratorExecutionRole"
  service_principals = ["lambda.amazonaws.com"]
  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

# Allows the Orchestrator to invoke Bedrock agents and read/write to S3
resource "aws_iam_policy" "orchestrator_permissions" {
  name        = "cams-ReadmeGeneratorOrchestratorPolicy"
  description = "Allows the Orchestrator Lambda to invoke Bedrock Agents and use the S3 bucket."

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "BedrockAgentInvoke"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent",
          "bedrock-agent-runtime:InvokeAgent"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3BucketOperations"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:HeadObject"
        ]
        Resource = "${module.s3_bucket.bucket_arn}/*"
      }
    ]
  })
}

# Attach the orchestrator-specific policy to the orchestrator role
resource "aws_iam_role_policy_attachment" "orchestrator_permissions_attach" {
  role       = module.orchestrator_execution_role.role_name
  policy_arn = aws_iam_policy.orchestrator_permissions.arn
}
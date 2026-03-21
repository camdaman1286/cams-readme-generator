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

# Trust policy - only allows YOUR specific repo on the main branch to assume this role
data "aws_iam_policy_document" "github_actions_trust_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::388691194728:oidc-provider/token.actions.githubusercontent.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:camdaman1286/cams-readme-generator:ref:refs/heads/main"]
    }
  }
}

# Dedicated role for GitHub Actions - separate from all other roles
resource "aws_iam_role" "github_actions_role" {
  name               = "cams-GitHubActionsRole-ReadmeGenerator"
  assume_role_policy = data.aws_iam_policy_document.github_actions_trust_policy.json
}

# NOTE: AdministratorAccess is used here for simplicity in a lab environment.
# In production, replace with a least-privilege custom policy.
resource "aws_iam_role_policy_attachment" "github_actions_permissions" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

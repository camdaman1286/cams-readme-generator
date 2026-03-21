# --- Shared IAM role for all pipeline Lambdas ---
# Reuses orchestrator permissions - needs Bedrock + S3 access
module "pipeline_lambda_role" {
  source             = "./modules/iam"
  role_name          = "cams-ReadmeGeneratorPipelineLambdaRole"
  service_principals = ["lambda.amazonaws.com"]
  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

resource "aws_iam_role_policy_attachment" "pipeline_lambda_permissions_attach" {
  role       = module.pipeline_lambda_role.role_name
  policy_arn = aws_iam_policy.orchestrator_permissions.arn
}

# --- invoke_repo_scanner ---
data "archive_file" "invoke_repo_scanner_zip" {
  type        = "zip"
  source_dir  = "${path.root}/src/invoke_repo_scanner"
  output_path = "${path.root}/dist/invoke_repo_scanner.zip"
}

resource "aws_lambda_function" "invoke_repo_scanner" {
  function_name    = "cams-InvokeRepoScanner"
  role             = module.pipeline_lambda_role.role_arn
  filename         = data.archive_file.invoke_repo_scanner_zip.output_path
  handler          = "lambda_function.handler"
  runtime          = "python3.11"
  timeout          = 60
  source_code_hash = data.archive_file.invoke_repo_scanner_zip.output_base64sha256

  environment {
    variables = {
      REPO_SCANNER_AGENT_ID       = module.repo_scanner_agent.agent_id
      REPO_SCANNER_AGENT_ALIAS_ID = "TSTALIASID"
      LOG_LEVEL                   = "INFO"
    }
  }
}

# --- invoke_summarizer ---
data "archive_file" "invoke_summarizer_zip" {
  type        = "zip"
  source_dir  = "${path.root}/src/invoke_summarizer"
  output_path = "${path.root}/dist/invoke_summarizer.zip"
}

resource "aws_lambda_function" "invoke_summarizer" {
  function_name    = "cams-InvokeSummarizer"
  role             = module.pipeline_lambda_role.role_arn
  filename         = data.archive_file.invoke_summarizer_zip.output_path
  handler          = "lambda_function.handler"
  runtime          = "python3.11"
  timeout          = 60
  source_code_hash = data.archive_file.invoke_summarizer_zip.output_base64sha256

  environment {
    variables = {
      PROJECT_SUMMARIZER_AGENT_ID       = module.project_summarizer_agent.agent_id
      PROJECT_SUMMARIZER_AGENT_ALIAS_ID = "TSTALIASID"
      LOG_LEVEL                         = "INFO"
    }
  }
}

# --- invoke_installation ---
data "archive_file" "invoke_installation_zip" {
  type        = "zip"
  source_dir  = "${path.root}/src/invoke_installation"
  output_path = "${path.root}/dist/invoke_installation.zip"
}

resource "aws_lambda_function" "invoke_installation" {
  function_name    = "cams-InvokeInstallation"
  role             = module.pipeline_lambda_role.role_arn
  filename         = data.archive_file.invoke_installation_zip.output_path
  handler          = "lambda_function.handler"
  runtime          = "python3.11"
  timeout          = 60
  source_code_hash = data.archive_file.invoke_installation_zip.output_base64sha256

  environment {
    variables = {
      INSTALLATION_GUIDE_AGENT_ID       = module.installation_guide_agent.agent_id
      INSTALLATION_GUIDE_AGENT_ALIAS_ID = "TSTALIASID"
      LOG_LEVEL                         = "INFO"
    }
  }
}

# --- invoke_usage ---
data "archive_file" "invoke_usage_zip" {
  type        = "zip"
  source_dir  = "${path.root}/src/invoke_usage"
  output_path = "${path.root}/dist/invoke_usage.zip"
}

resource "aws_lambda_function" "invoke_usage" {
  function_name    = "cams-InvokeUsage"
  role             = module.pipeline_lambda_role.role_arn
  filename         = data.archive_file.invoke_usage_zip.output_path
  handler          = "lambda_function.handler"
  runtime          = "python3.11"
  timeout          = 60
  source_code_hash = data.archive_file.invoke_usage_zip.output_base64sha256

  environment {
    variables = {
      USAGE_EXAMPLES_AGENT_ID       = module.usage_examples_agent.agent_id
      USAGE_EXAMPLES_AGENT_ALIAS_ID = "TSTALIASID"
      LOG_LEVEL                     = "INFO"
    }
  }
}

# --- invoke_compiler ---
data "archive_file" "invoke_compiler_zip" {
  type        = "zip"
  source_dir  = "${path.root}/src/invoke_compiler"
  output_path = "${path.root}/dist/invoke_compiler.zip"
}

resource "aws_lambda_function" "invoke_compiler" {
  function_name    = "cams-InvokeCompiler"
  role             = module.pipeline_lambda_role.role_arn
  filename         = data.archive_file.invoke_compiler_zip.output_path
  handler          = "lambda_function.handler"
  runtime          = "python3.11"
  timeout          = 60
  source_code_hash = data.archive_file.invoke_compiler_zip.output_base64sha256

  environment {
    variables = {
      FINAL_COMPILER_AGENT_ID       = module.final_compiler_agent.agent_id
      FINAL_COMPILER_AGENT_ALIAS_ID = "TSTALIASID"
      OUTPUT_BUCKET                 = module.s3_bucket.bucket_id
      LOG_LEVEL                     = "INFO"
    }
  }
}

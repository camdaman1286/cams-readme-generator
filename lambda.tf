# Package the repo scanner Python code into a zip for deployment
data "archive_file" "repo_scanner_zip" {
  type        = "zip"
  source_dir  = "${path.root}/src/repo_scanner"
  output_path = "${path.root}/dist/repo_scanner.zip"
}

# Deploy the repo scanner Lambda function
resource "aws_lambda_function" "repo_scanner_lambda" {
  function_name    = "cams-RepoScannerTool"
  role             = module.lambda_execution_role.role_arn
  filename         = data.archive_file.repo_scanner_zip.output_path
  handler          = "lambda_function.handler"
  runtime          = "python3.11"
  timeout          = 30
  source_code_hash = data.archive_file.repo_scanner_zip.output_base64sha256

  # This layer provides the git binary inside the Lambda environment
  layers = ["arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8"]
}

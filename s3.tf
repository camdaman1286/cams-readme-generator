module "s3_bucket" {
  source      = "./modules/s3"
  bucket_name = "cams-readme-generator-${random_string.suffix.result}"
}

# Triggers the Orchestrator Lambda whenever a file is uploaded to inputs/
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = module.s3_bucket.bucket_id

  lambda_function {
    lambda_function_arn = aws_lambda_function.orchestrator_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "inputs/"
  }

  depends_on = [aws_lambda_permission.allow_s3_to_invoke_orchestrator]
}
# S3 bucket to store Terraform state remotely - required for CI/CD pipeline
resource "random_string" "state_bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "cams-tf-readme-generator-state-${random_string.state_bucket_suffix.result}"
}

# DynamoDB table for Terraform state locking - prevents concurrent apply conflicts
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "cams-readme-generator-tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

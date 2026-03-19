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
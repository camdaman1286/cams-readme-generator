# Remote state backend - allows CI/CD pipeline to access and update infrastructure state
terraform {
  backend "s3" {
    bucket         = "cams-tf-readme-generator-state-gvfmisuo"
    key            = "global/s3/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "cams-readme-generator-tf-locks"
  }
}

module "s3_bucket" {
  source      = "./modules/s3"
  bucket_name = "cams-readme-generator-${random_string.suffix.result}"
}

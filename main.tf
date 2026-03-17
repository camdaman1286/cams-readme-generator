terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Generates a random suffix to ensure globally unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

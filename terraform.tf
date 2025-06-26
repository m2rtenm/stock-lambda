terraform {
  backend "s3" {
    bucket  = "marten-tfstate"
    key     = "stock-lambda/terraform.tfstate"
    region  = "eu-north-1"
    profile = "sec"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.1"
    }
  }

  required_version = ">= 1.5.0"
}

provider "aws" {
  region  = var.region
  profile = "prod"
}
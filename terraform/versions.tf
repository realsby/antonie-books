terraform {
  required_version = ">= 1.11"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 2.19"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  # Keep the state in S3. The database password is not in the state (see database.tf),
  # but keep the bucket private anyway. Fill in the values with:
  #   terraform init -backend-config="bucket=<bucket>" -backend-config="key=books-api/terraform.tfstate" -backend-config="region=eu-west-1"
  backend "s3" {
    use_lockfile = true
    encrypt      = true
  }
}

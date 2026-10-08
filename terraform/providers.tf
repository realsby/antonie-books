provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.name
      ManagedBy = "terraform"
    }
  }
}

# The Atlas login comes from env variables, so it is not in the code. See README.md.
provider "mongodbatlas" {}

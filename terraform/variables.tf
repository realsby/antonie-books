variable "name" {
  description = "Name for all resources."
  type        = string
  default     = "books-api"
}

variable "aws_region" {
  description = "AWS region. The Atlas cluster runs in the same region."
  type        = string
  default     = "eu-west-1"
}

variable "vpc_cidr" {
  description = "IP range of the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "certificate_arn" {
  description = "ACM certificate for HTTPS on the load balancer."
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to run. Tags can not change, so use a new tag for each release (for example the git commit)."
  type        = string
}

variable "min_tasks" {
  description = "Smallest number of running containers. Use 2 or more, so one AZ can fail."
  type        = number
  default     = 2
}

variable "max_tasks" {
  description = "Largest number of running containers."
  type        = number
  default     = 6
}

variable "atlas_org_id" {
  description = "MongoDB Atlas organization id."
  type        = string
}

variable "atlas_instance_size" {
  description = "Atlas cluster size. M10 is the smallest size with private endpoints."
  type        = string
  default     = "M10"
}

variable "db_name" {
  description = "Name of the MongoDB database."
  type        = string
  default     = "books"
}

variable "db_password_version" {
  description = "Add 1 to make a new database password."
  type        = number
  default     = 1
}

# The containers have no internet. They reach AWS services with VPC endpoints:
#   ecr.api, ecr.dkr: pull the Docker image
#   logs:             send logs to CloudWatch
#   secretsmanager:   read the database password
# The Atlas endpoint is in database.tf.

locals {
  aws_services = ["ecr.api", "ecr.dkr", "logs", "secretsmanager"]
}

resource "aws_vpc_endpoint" "aws" {
  for_each = toset(local.aws_services)

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.name}-${each.key}" }
}

# ECR keeps the image layers in S3. The S3 gateway endpoint is free.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = { Name = "${var.name}-s3" }
}

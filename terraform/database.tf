# MongoDB Atlas cluster. The containers reach it with AWS PrivateLink,
# so the traffic stays inside AWS. The cluster has no public access.

locals {
  # "eu-west-1" -> "EU_WEST_1". This is the Atlas name of the same AWS region.
  atlas_region = upper(replace(var.aws_region, "-", "_"))
}

resource "mongodbatlas_project" "main" {
  name   = var.name
  org_id = var.atlas_org_id
}

# --- Private connection (PrivateLink)

# 1. Atlas makes an endpoint service in its own AWS account.
resource "mongodbatlas_privatelink_endpoint" "main" {
  project_id    = mongodbatlas_project.main.id
  provider_name = "AWS"
  region        = local.atlas_region
}

# 2. We make an endpoint in our VPC that connects to it.
resource "aws_vpc_endpoint" "atlas" {
  vpc_id             = aws_vpc.main.id
  service_name       = mongodbatlas_privatelink_endpoint.main.endpoint_service_name
  vpc_endpoint_type  = "Interface"
  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.atlas.id]

  tags = { Name = "${var.name}-atlas" }
}

# 3. We tell Atlas to accept our endpoint.
resource "mongodbatlas_privatelink_endpoint_service" "main" {
  project_id          = mongodbatlas_privatelink_endpoint.main.project_id
  private_link_id     = mongodbatlas_privatelink_endpoint.main.private_link_id
  endpoint_service_id = aws_vpc_endpoint.atlas.id
  provider_name       = "AWS"
}

# --- Cluster

resource "mongodbatlas_advanced_cluster" "main" {
  project_id             = mongodbatlas_project.main.id
  name                   = var.name
  cluster_type           = "REPLICASET"
  mongo_db_major_version = "8.0"

  backup_enabled                 = true
  termination_protection_enabled = true

  # 3 nodes in our region. Atlas puts them in different AZs.
  replication_specs = [{
    region_configs = [{
      provider_name = "AWS"
      region_name   = local.atlas_region
      priority      = 7
      electable_specs = {
        instance_size = var.atlas_instance_size
        node_count    = 3
      }
    }]
  }]

  # The private connection string exists only when the endpoint is ready.
  depends_on = [mongodbatlas_privatelink_endpoint_service.main]
}

locals {
  # We have one private endpoint, so [0] is ours.
  mongo_url = mongodbatlas_advanced_cluster.main.connection_strings.private_endpoint[0].srv_connection_string
}

# --- App user and password

# "ephemeral" and "_wo" (write-only) mean: Terraform sends the password to Atlas
# and to Secrets Manager, but it does not save it in the state.
# To make a new password, add 1 to var.db_password_version.
ephemeral "random_password" "db" {
  length  = 40
  special = false
}

resource "mongodbatlas_database_user" "app" {
  project_id         = mongodbatlas_project.main.id
  username           = var.name
  auth_database_name = "admin"

  password_wo         = ephemeral.random_password.db.result
  password_wo_version = var.db_password_version

  # The app can only read and write its own database.
  roles {
    role_name     = "readWrite"
    database_name = var.db_name
  }

  # The user only works on this cluster.
  scopes {
    name = mongodbatlas_advanced_cluster.main.name
    type = "CLUSTER"
  }
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.name}/db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id                = aws_secretsmanager_secret.db_password.id
  secret_string_wo         = ephemeral.random_password.db.result
  secret_string_wo_version = var.db_password_version
}

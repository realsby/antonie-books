# Terraform: AWS setup

This folder has the AWS setup to run the Books API in production.

```
                  Internet
                     |
                     |  HTTPS (443). HTTP (80) only redirects to HTTPS.
                     v
   +-----------------------------------+
   |  Application Load Balancer        |   public subnets, 2 AZs
   +-----------------------------------+
                     |
                     |  port 8000
                     v
   +-----------------------------------+
   |  ECS Fargate tasks (the API)      |   private subnets, 2 AZs
   |  2 to 6 containers                |   no internet access
   +-----------------------------------+
          |                       |
          | 443                   | 1024-65535
          v                       v
   +----------------+     +---------------------+    PrivateLink    +--------------------+
   | VPC endpoints  |     | Atlas private       | ----------------> | MongoDB Atlas      |
   | ECR, S3, Logs, |     | endpoint            |  (inside AWS)     | M10, 3 nodes       |
   | Secrets Mgr    |     +---------------------+                   +--------------------+
   +----------------+
```

## Files

| File | What is in it |
|---|---|
| `versions.tf` | Terraform and provider versions, S3 state |
| `providers.tf` | AWS and Atlas providers |
| `variables.tf` | Input values |
| `network.tf` | VPC, subnets, routes, flow logs |
| `endpoints.tf` | VPC endpoints for AWS services |
| `security.tf` | Security groups |
| `alb.tf` | Load balancer, HTTPS |
| `ecr.tf` | Docker image repository |
| `ecs.tf` | ECS cluster, task, service, IAM roles, auto scaling |
| `database.tf` | Atlas project, cluster, PrivateLink, database user, password secret |
| `outputs.tf` | URLs and names you need after `apply` |

## Decisions

### Container hosting: ECS Fargate

- There are no servers to manage or patch. AWS runs the containers.
- It is simple for one service. Kubernetes (EKS) is too much for one small API.
- At least 2 tasks run, in 2 AZs. If one AZ fails, the API still works.
- Auto scaling adds tasks when the CPU is over 60%. It uses 2 to 6 tasks.
- Deploys are rolling. If the new version does not start, ECS goes back to the old version (circuit breaker).
- Tasks run on ARM (Graviton). It is cheaper than x86.

### Load balancer

- An Application Load Balancer in the public subnets. It is the only public part.
- HTTPS only, with TLS 1.2 and 1.3. You need an ACM certificate for your domain.
- It checks `GET /health` on each task. A task that does not answer gets no traffic.

### Database: MongoDB Atlas

- **Why Atlas, and not Amazon DocumentDB?**
  - Atlas is real MongoDB 8.0. It is the same database that we use locally and in the tests. So if the tests pass locally, the code also works in production. All features (`$lookup`, collation for "ignore case") work the same way.
  - DocumentDB is a different database. It is only *compatible* with MongoDB, and not every feature works the same. If we used DocumentDB, our local tests would not be enough. We would need to test the app again on DocumentDB.
- Atlas manages backups, updates and failover for us.
- The cluster is a replica set with 3 nodes in our AWS region. Backup and termination protection are on.
- `M10` is the smallest size that supports private endpoints.

### How the containers reach the database

- **AWS PrivateLink.** Atlas makes an endpoint service. We make a VPC endpoint in our private subnets that connects to it. The traffic stays inside AWS. It does not go over the internet.
- The Atlas project has **no IP access list**, so the cluster has no public access.
- Only the API security group can reach the Atlas endpoint. Atlas uses ports 1024-65535 for PrivateLink, not 27017.
- The app gets the private connection string in the `MONGO_URL` env variable.

### No internet for the containers

The private subnets have **no route to the internet** and no NAT gateway. The containers reach AWS services with VPC endpoints:

| Endpoint | Why |
|---|---|
| `ecr.api`, `ecr.dkr` | Pull the Docker image |
| `s3` (gateway, free) | ECR keeps the image layers in S3 |
| `logs` | Send logs to CloudWatch |
| `secretsmanager` | Read the database password |

The cost is close to 2 NAT gateways, but there is no way out to the internet. If the app needs to call an outside service later, we can add a NAT gateway.

### Secrets

- Terraform makes a random database password. It sends the password to Atlas and to Secrets Manager.
- It uses `ephemeral` and write-only (`_wo`) arguments, so **the password is not saved in the Terraform state**.
- ECS reads the password when a task starts. The app gets it as `MONGO_PASSWORD`.
- Only the ECS execution role can read this secret. The app role (task role) has no AWS permissions, because the app does not call AWS.
- The database user can only read and write the `books` database, and only on this cluster.

### Other security points

- ECR tags can not change (immutable), and ECR scans every image on push.
- The container runs as a normal user (not root), with a read-only file system.
- VPC flow logs save all blocked traffic.
- `trivy config .` finds 0 problems. A few checks are ignored on purpose, with the reason in a comment:
  - The load balancer is public, because this is a public API.
  - Logs, images and the secret use AWS-managed encryption keys, not our own KMS keys. This is enough here and keeps the setup simple.

## How to use it

> I checked this setup with `terraform fmt`, `terraform validate` (Terraform 1.16.5, AWS provider 6.68.0, Atlas provider 2.19.0) and `trivy config`. I did not run `terraform apply` on real accounts.

You need:

- Terraform 1.11 or newer
- AWS credentials
- An Atlas organization and an Atlas service account. Set it with env variables:
  ```bash
  export MONGODB_ATLAS_CLIENT_ID=...
  export MONGODB_ATLAS_CLIENT_SECRET=...
  ```
- An ACM certificate for your domain
- An S3 bucket for the Terraform state

Steps:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in the values

terraform init \
  -backend-config="bucket=<state-bucket>" \
  -backend-config="key=books-api/terraform.tfstate" \
  -backend-config="region=eu-west-1"

# 1. Make the image repository first.
terraform apply -target=aws_ecr_repository.app

# 2. Build and push the image. Use the git commit as the tag.
ECR=$(terraform output -raw ecr_repository_url)
TAG=$(git rev-parse --short HEAD)
aws ecr get-login-password | docker login --username AWS --password-stdin "${ECR%%/*}"
docker build --platform linux/arm64 -t "$ECR:$TAG" ..
docker push "$ECR:$TAG"

# 3. Make everything else. Creating the Atlas cluster and PrivateLink takes some time.
terraform apply -var "image_tag=$TAG"
```

Then point your domain (CNAME) to the load balancer. `terraform output api_url` shows its address.

**New release:** build and push a new tag, then run `terraform apply -var "image_tag=<new-tag>"`.

**New database password:** add 1 to `db_password_version`, run `terraform apply`, then start new tasks:

```bash
aws ecs update-service --cluster books-api --service books-api --force-new-deployment
```

Running tasks still have the old password. New database connections fail until the new tasks run. So do this in a quiet time.

## Next steps

These are not in this setup, but I would add them for a real production system:

- CI/CD with GitHub Actions. It would log in to AWS with OIDC, with no stored keys.
- AWS WAF in front of the load balancer
- CloudWatch alarms (5xx errors, CPU, unhealthy tasks) and Atlas alerts
- Route 53 and the ACM certificate in Terraform
- A password change with no downtime: use two database users and switch between them

output "api_url" {
  description = "Point your domain (CNAME) to the load balancer, then use https://<your-domain>."
  value       = "https://${aws_lb.main.dns_name}"
}

output "ecr_repository_url" {
  description = "Push the Docker image here."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service" {
  value = aws_ecs_service.app.name
}

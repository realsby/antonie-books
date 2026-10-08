# Traffic can only go: internet -> load balancer -> containers -> Atlas endpoint.

resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "Load balancer. Open to the internet on 80 and 443."
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  description       = "HTTP. Only redirects to HTTPS."
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "HTTPS"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  description                  = "To the containers"
}

resource "aws_security_group" "app" {
  name        = "${var.name}-app"
  description = "API containers. Only the load balancer can reach them."
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  description                  = "From the load balancer"
}

resource "aws_vpc_security_group_egress_rule" "app_out" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "ECR, CloudWatch Logs, Secrets Manager (via NAT) and Atlas (via the private endpoint)"
}

resource "aws_security_group" "atlas" {
  name        = "${var.name}-atlas"
  description = "Atlas private endpoint. Only the containers can reach it."
  vpc_id      = aws_vpc.main.id
}

# Atlas uses ports 1024-65535 on the private endpoint (not 27017).
resource "aws_vpc_security_group_ingress_rule" "atlas_from_app" {
  security_group_id            = aws_security_group.atlas.id
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 1024
  to_port                      = 65535
  description                  = "From the containers"
}

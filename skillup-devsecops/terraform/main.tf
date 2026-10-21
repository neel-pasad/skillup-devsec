data "aws_availability_zones" "available" {
  state = "available"
}

# Latest Ubuntu 24.04 LTS AMI (resolved from Canonical's public SSM parameter)
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

# Lets the EC2 instance pull the image from ECR without storing any access keys on the server
resource "aws_iam_role" "ec2_ecr_read" {
  count = var.attach_ecr_role ? 1 : 0
  name  = "skillup-ec2-ecr-read"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  count      = var.attach_ecr_role ? 1 : 0
  role       = aws_iam_role.ec2_ecr_read[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2_ecr_read" {
  count = var.attach_ecr_role ? 1 : 0
  name  = "skillup-ec2-ecr-read"
  role  = aws_iam_role.ec2_ecr_read[0].name
}

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "skillup-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "skillup-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = false # the instance gets its address explicitly below
  tags                    = { Name = "skillup-public-subnet" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "skillup-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "web" {
  name        = "skillup-web-sg"
  description = "Allow web traffic, restricted SSH, and limited outbound traffic"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "skillup-web-sg" }
}

#trivy:ignore:AVD-AWS-0107 -- a public website must accept HTTP from the internet (TLS via ALB is future scope)
resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.web.id
  description       = "Public HTTP to the website"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.web.id
  description       = "SSH only from the administrator IP"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = var.allowed_ssh_cidr
}

# Outbound: HTTPS (package and image downloads), HTTP (OS repos) and DNS only
#trivy:ignore:AVD-AWS-0104 -- outbound is limited to ports 443, 80 and 53 which the instance needs to pull packages and the Docker image
resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.web.id
  description       = "HTTPS out"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

#trivy:ignore:AVD-AWS-0104 -- see rule above
resource "aws_vpc_security_group_egress_rule" "http_out" {
  security_group_id = aws_security_group.web.id
  description       = "HTTP out (OS repositories)"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

#trivy:ignore:AVD-AWS-0104 -- see rule above
resource "aws_vpc_security_group_egress_rule" "dns" {
  security_group_id = aws_security_group.web.id
  description       = "DNS out"
  ip_protocol       = "udp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_instance" "web" {
  ami                         = data.aws_ssm_parameter.ubuntu.value
  iam_instance_profile        = var.attach_ecr_role ? aws_iam_instance_profile.ec2_ecr_read[0].name : null
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = true
  key_name                    = var.key_name
  monitoring                  = true

  user_data = file("${path.module}/user_data.sh")
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 only
  }

  root_block_device {
    volume_size = 12
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "skillup-web" }
}

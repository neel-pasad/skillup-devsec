variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "allowed_ssh_cidr" {
  description = "Your public IP in CIDR form (x.x.x.x/32) allowed to SSH. Never use 0.0.0.0/0."
  type        = string
  validation {
    condition     = var.allowed_ssh_cidr != "0.0.0.0/0"
    error_message = "SSH must not be open to the whole internet."
  }
}

variable "instance_type" {
  description = "EC2 instance size (t3.micro is free-tier eligible in most regions)"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of an EXISTING EC2 key pair (create it in the console: EC2 > Key pairs). Needed to SSH in."
  type        = string
}

variable "attach_ecr_role" {
  description = "Attach an IAM role so the instance can pull from ECR. Set false if your lab account blocks IAM, then use aws configure on the server."
  type        = bool
  default     = true
}

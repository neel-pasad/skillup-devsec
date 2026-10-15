variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "docker_image" {
  description = "Docker image to run, e.g. youruser/skillup:5"
  type        = string
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
  description = "Existing EC2 key pair name for SSH (leave empty to disable SSH access)"
  type        = string
  default     = ""
}

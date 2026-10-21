output "public_ip" {
  description = "Public IP of the web server"
  value       = aws_instance.web.public_ip
}

output "website_url" {
  description = "URL of the deployed website"
  value       = "http://${aws_instance.web.public_ip}"
}

output "ssh_command" {
  description = "Command to connect to the server (replace the .pem path)"
  value       = "ssh -i <path-to-${var.key_name}.pem> ubuntu@${aws_instance.web.public_ip}"
}

#!/bin/bash
# Runs once at first boot on Ubuntu: install Docker and the AWS CLI.
# The container is started by hand with the docker CLI (see docs/RUNBOOK.md, step 9).
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io unzip curl
systemctl enable --now docker
usermod -aG docker ubuntu
curl -s https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscliv2.zip
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install

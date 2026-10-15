#!/bin/bash
# Runs once at first boot: install Docker and start the SkillUp container.
set -euxo pipefail
dnf install -y docker
systemctl enable --now docker
docker pull ${docker_image}
docker run -d --name skillup --restart always -p 80:8000 ${docker_image}

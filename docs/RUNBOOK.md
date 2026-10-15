# RUNBOOK: how to run every DevSecOps step yourself

Everything below was prepared and checked as far as possible without Docker, Jenkins, SonarQube or AWS.
**Steps marked ▶ you must run on your own machine**; take the screenshot listed at each step.
Never show passwords, tokens or AWS keys in a screenshot or the video (blur or crop them).

## 0. Prerequisites (Ubuntu / WSL2 example, verify versions)
Python 3.12, Git, Docker, Java 17 (for Jenkins), Terraform >= 1.5, Trivy, AWS CLI, a GitHub account, a Docker Hub account, an AWS account (free tier).

## 1. Run the website locally
```
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest --cov=app                                      # expect 30 passed
PORT=5055 python -m app.server                        # open http://127.0.0.1:5055
```
Screenshot: terminal with `30 passed`, browser with the website.

## 2. ▶ Git and GitHub (Version Control)
```
git init && git add . && git commit -m "Initial commit"      # (history is already prepared in this folder)
git branch -M main
git remote add origin https://github.com/<your-username>/skillup-devsecops.git
git push -u origin main
```
Create the empty repository on GitHub first. Use a Personal Access Token or SSH key (do not show it).
Screenshot: GitHub repo page with commits and files (Dockerfile, Jenkinsfile, terraform/). Put the URL in the report.

## 3. ▶ Docker
```
docker build -t <dockerhub-user>/skillup:1 .
docker run -d --name skillup -p 8000:8000 <dockerhub-user>/skillup:1
curl http://localhost:8000/health              # {"status":"ok",...}
docker ps                                       # STATUS should become (healthy)
docker login && docker push <dockerhub-user>/skillup:1
```
Screenshots: `docker build` finishing, `docker ps` (healthy), website at localhost:8000.

## 4. ▶ SonarQube
```
docker compose -f docker-compose.tools.yml up -d       # http://localhost:9000, login admin/admin then change password
```
In SonarQube: My Account > Security > generate a token. Then
```
sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=<TOKEN>
```
(sonar-project.properties is already configured). Screenshot: project dashboard (Quality Gate, Bugs, Vulnerabilities, Code Smells, Coverage). Hide the token.

## 5. ▶ Trivy
```
trivy fs --scanners vuln,secret --severity HIGH,CRITICAL .
trivy config .
trivy image <dockerhub-user>/skillup:1
```
Screenshots of each output. Copy the real numbers into `docs/VULNERABILITY_REPORT.md` and the report (Section 8).
Already-produced results that need no extra tools are in `docs/scans/`.

## 6. ▶ Jenkins
1. Install Jenkins (https://www.jenkins.io/doc/book/installing/) on a machine that also has python3, docker, trivy, terraform and sonar-scanner on PATH; add the `jenkins` user to the `docker` group.
2. Plugins: Pipeline, Git, Credentials Binding, SonarQube Scanner, Docker Pipeline, JUnit, AWS Credentials.
3. Manage Jenkins > Credentials: add `dockerhub-creds` (Username with password) and `aws-creds` (AWS Credentials: access key + secret of an IAM user with EC2/VPC permissions).
4. Manage Jenkins > System > SonarQube servers: name **sonarqube**, URL http://localhost:9000, add the token as a Secret text credential.
5. New Item > Pipeline > "Pipeline script from SCM" > Git > your GitHub URL, branch `main`, script path `Jenkinsfile`.
6. Edit `IMAGE_NAME` at the top of `Jenkinsfile` to your Docker Hub name, commit, push.
7. Build with parameters: first with DEPLOY_TO_AWS = false (build/test/scan/push), then true.
Screenshots: pipeline Stage View (all green), Console Output end, security stages, test results.

## 7. ▶ Terraform and AWS
```
aws configure                      # use an IAM user, NOT the root account; never show the keys
cd terraform
cp terraform.tfvars.example terraform.tfvars    # edit: docker_image, allowed_ssh_cidr (your IP/32)
terraform init
terraform validate
terraform plan
terraform apply                    # type yes
terraform output website_url       # open it in the browser (wait ~2 minutes after apply)
```
Screenshots: `terraform plan` summary, `terraform apply` complete, the EC2 instance in the AWS console, the website at the public IP.
**Destroy when finished to avoid charges:** `terraform destroy`.

## 8. Demo video checklist (record screen, 5-8 minutes)
Website demo > Docker (build/run/ps) > Jenkins pipeline run > Terraform files + apply + AWS console > SonarQube + Trivy results > vulnerability report. Hide credentials. Post on LinkedIn and add the link to the report.

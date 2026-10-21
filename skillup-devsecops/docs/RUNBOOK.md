# RUNBOOK: do the micro project step by step (in your teacher's order)

Teacher's checklist: **1 application ready → 2 GitHub → 3 dockerize → 4 Trivy image scan with report → 5 SonarQube SAST with report → 6 Jenkins CI/CD → 7 Terraform creates AWS EC2 (Ubuntu) → run the image pushed on ECR with the docker CLI → show the app on the public IP on the proper port.**

Commands below are for **macOS (Homebrew)**; on Ubuntu/WSL use `apt`/the vendor install pages instead. Take a screenshot where you see 📸. **Never show passwords, tokens, access keys or your AWS account ID.**
Replace `YOURUSER` with your GitHub username and `ap-south-1` with your region if different.

---
## STEP 0: One-time setup (15-20 min)
```bash
brew install git python@3.12 trivy awscli sonar-scanner openjdk@17 jenkins-lts
brew install --cask docker                      # Docker Desktop: open it once and wait for "running"
brew tap hashicorp/tap && brew install hashicorp/tap/terraform
```
Accounts: **GitHub**, **AWS** (free tier). In AWS Console: IAM → Users → Create user → attach `AmazonEC2FullAccess`, `AmazonEC2ContainerRegistryFullAccess`, `IAMFullAccess` → Security credentials → Create access key (CLI). Then:
```bash
aws configure          # paste key, secret, region (ap-south-1), output: json   (do not show this on screen)
aws sts get-caller-identity   # proves it works
```
AWS lab/college account that blocks IAM? Set `attach_ecr_role = false` in step 7 and use `aws configure` on the server in step 9.

## STEP 1: Application ready (2 min)
```bash
cd skillup-devsecops
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=app                  # 30 passed
python -m app.server              # open http://127.0.0.1:5055  (Ctrl+C to stop)
```
📸 terminal `30 passed` + website in browser.

## STEP 2: GitHub (3 min)
1. github.com → New repository → name `skillup-devsecops` → **Public** (easiest for Jenkins) → no README → Create.
```bash
git remote add origin https://github.com/YOURUSER/skillup-devsecops.git
git branch -M main
git push -u origin main           # login with a Personal Access Token (Settings → Developer settings → Tokens) when asked for password
```
📸 repo page showing Dockerfile, Jenkinsfile, terraform/ and the commit list. Save the URL for the report.

## STEP 3: Dockerize (3 min)
```bash
docker build -t skillup:1 .
docker run -d --name skillup -p 8000:8000 skillup:1
curl http://localhost:8000/health        # {"status":"ok",...}
docker ps                                 # wait ~30s: STATUS (healthy)
```
Open http://localhost:8000. 📸 `docker build` end, `docker ps` (healthy), website. Then `docker rm -f skillup`.

## STEP 4: Trivy image scan with report (3 min)
```bash
trivy image skillup:1                                   # 📸 shows the vulnerability table
IMAGE=skillup:1 bash scripts/make_scan_reports.sh       # writes reports/trivy-image-report.txt / .json / .html
open reports/trivy-image-report.html                    # 📸 the HTML report
```
First run downloads the vulnerability database (needs internet, 1-2 min). Copy the counts (CRITICAL/HIGH/MEDIUM/LOW) into report Section 5.2. **If HIGH/CRITICAL are found:** note them in the report (severity, package, fixed version) and fix by upgrading the package in `requirements.txt` or using a newer base image tag, rebuild, rescan; this "found → fixed → rescanned" story earns marks.

## STEP 5: SonarQube SAST with report (10 min)
```bash
docker compose -f docker-compose.tools.yml up -d        # wait ~1-2 min, open http://localhost:9000
```
Login `admin` / `admin` → set a new password → top-right avatar → My Account → Security → **Generate token** (type: User/Global) → copy it.
```bash
source .venv/bin/activate && pytest --cov=app           # creates coverage.xml for Sonar
sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=PASTE_TOKEN
```
Open the project `SkillUp DevSecOps` in the browser. 📸 **Overview** (Quality Gate, Bugs, Vulnerabilities, Hotspots, Coverage), **Issues** tab, **Security Hotspots** tab.
Report files: `SONAR_TOKEN=PASTE_TOKEN bash scripts/make_scan_reports.sh` also saves `reports/sonar-*.json`. Write the numbers into report Section 5.2.

## STEP 6: Jenkins CI/CD setup (15 min)
```bash
brew services start jenkins-lts            # open http://localhost:8080
cat ~/.jenkins/secrets/initialAdminPassword    # first-login password (do not show)
```
1. Install suggested plugins, create admin user.
2. Manage Jenkins → Plugins → Available: install **SonarQube Scanner**, **AWS Credentials**, **Pipeline** (usually present). Restart if asked.
3. Manage Jenkins → Credentials → Global → Add: kind **AWS Credentials**, ID `aws-creds`, paste your access key + secret.
4. Manage Jenkins → Credentials → Add: kind **Secret text**, ID `sonar-token`, value = SonarQube token.
5. Manage Jenkins → System → **SonarQube servers** → Add: name `sonarqube`, URL `http://localhost:9000`, token `sonar-token`. Save.
6. New Item → name `skillup-pipeline` → **Pipeline** → Pipeline script from SCM → Git → URL `https://github.com/YOURUSER/skillup-devsecops.git` → branch `*/main` → script path `Jenkinsfile` → Save.
7. **Build with Parameters** → leave RUN_TERRAFORM unchecked for the first run → Build.
📸 Stage View (green), Console Output end (`Finished: SUCCESS`), test result.
The run pushes the image to **ECR** automatically (stage "Push Image to Amazon ECR") and creates the repo `skillup` if missing. If a stage fails, open Console Output, read the last red lines, fix, `git commit`, `git push`, build again.

## STEP 7: Terraform creates the AWS EC2 machine (Ubuntu) (10 min)
```bash
aws ec2 create-key-pair --key-name skillup-key --query KeyMaterial --output text > skillup-key.pem
chmod 400 skillup-key.pem                  # never commit this file (.pem is git-ignored)
cd terraform
cp terraform.tfvars.example terraform.tfvars
curl -s https://checkip.amazonaws.com       # your public IP -> put YOURIP/32 as allowed_ssh_cidr in terraform.tfvars
# edit terraform.tfvars: allowed_ssh_cidr = "YOURIP/32", key_name = "skillup-key"
terraform init
terraform validate
terraform plan                              # 📸 summary: N to add
terraform apply                             # type yes   📸 Apply complete
terraform output                            # public_ip, website_url, ssh_command
```
📸 AWS Console → EC2 → Instances (running, Ubuntu) and its Security group. (Alternatively tick RUN_TERRAFORM in Jenkins and fill KEY_NAME and ALLOWED_SSH_CIDR.)

## STEP 8: Image on ECR (2 min; Jenkins already did this)
```bash
aws ecr describe-images --repository-name skillup --query 'imageDetails[].imageTags'    # 📸 shows your tag e.g. ["1"]
```
Console alternative: ECR → Repositories → skillup. 📸 image with tag. **Jenkins failed or skipped?** push by hand:
```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text); REG=$ACCOUNT.dkr.ecr.ap-south-1.amazonaws.com
aws ecr create-repository --repository-name skillup --region ap-south-1 || true
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $REG
docker tag skillup:1 $REG/skillup:1 && docker push $REG/skillup:1
```

## STEP 9: Run the ECR image on EC2 with the docker CLI, show it on the public IP (5 min)
```bash
ssh -i skillup-key.pem ubuntu@PUBLIC_IP          # PUBLIC_IP from terraform output
cloud-init status --wait                         # wait until "status: done" (Docker + AWS CLI install, ~2 min)
docker --version && aws --version
```
On the server (if you used `attach_ecr_role = false`, first run `aws configure`):
```bash
REGION=ap-south-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text); REG=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REG
docker pull $REG/skillup:1                       # use your tag
docker run -d --name skillup --restart always -p 80:8000 $REG/skillup:1
docker ps                                        # 📸 container running (healthy)
curl localhost/health
```
Port mapping: the app listens on **8000 inside the container**; `-p 80:8000` publishes it on **port 80** of the server, which the security group allows. In your browser open **http://PUBLIC_IP** (not https). 📸 website loading on the public IP **with the IP visible in the address bar** (this is what the teacher asked to see).

## STEP 10: Clean up (avoid AWS charges)
```bash
exit                                   # leave the server
cd terraform && terraform destroy      # type yes
aws ecr delete-repository --repository-name skillup --force --region ap-south-1
docker rm -f skillup 2>/dev/null; docker compose -f ../docker-compose.tools.yml down
```

---
## Demo order for your teacher (5-7 min)
1. VS Code: show project + `git log` + GitHub page. 2. `docker ps` (healthy). 3. Trivy report (HTML). 4. SonarQube dashboard. 5. Jenkins Stage View (green). 6. `terraform apply` output + EC2 in console. 7. ECR image. 8. Browser: **http://PUBLIC_IP**.

## Quick fixes
| Problem | Fix |
|---|---|
| `docker: command not found` / daemon error | Open Docker Desktop and wait until it says running |
| Jenkins "docker/trivy/terraform: not found" | Install with brew; Jenkinsfile already adds `/opt/homebrew/bin` to PATH; restart Jenkins: `brew services restart jenkins-lts` |
| Jenkins can't pull Python packages / Trivy DB | Check internet/VPN; re-run |
| Sonar "Quality Gate failed" | Open Sonar Issues, fix or mark reviewed, push, rebuild |
| `terraform apply` AccessDenied / IAM error | Set `attach_ecr_role = false`, or ask for IAM permission |
| SSH timeout | `allowed_ssh_cidr` must be your CURRENT public IP /32 (it changes on a new network) |
| Browser can't open IP | Wait 2-3 min; use `http://` not `https://`; check `docker ps` on server; security group has port 80 |
| `Permission denied` on .pem | `chmod 400 skillup-key.pem` |

# SkillUp: Online Skill Development Platform (DevSecOps Lab CIAP)

Learners search and enrol in courses, study lessons, take quizzes and earn certificates; instructors create courses and admins approve them.
The platform logic was modelled with DFD and UML in the Software Engineering Practices (SEP) project and is now delivered with DevSecOps practices.
Supports **SDG 9: Industry, Innovation & Infrastructure** (secure, reliable, automated digital infrastructure) and SDG 4.

| Folder / file | Purpose |
|---|---|
| `app/` | Website: `skillup.py` (business rules), `server.py` (Flask API + security headers), `static/index.html` (UI) |
| `tests/` | 30 automated tests (20 business-rule + 10 API/security) |
| `Dockerfile`, `.dockerignore` | Container image (non-root, health check, gunicorn) |
| `Jenkinsfile` | CI/CD: test, Bandit, SonarQube, Trivy, Docker, Terraform, deploy |
| `sonar-project.properties` | SonarQube configuration |
| `terraform/` | AWS infrastructure: VPC, subnet, security group, EC2 running the container |
| `docs/` | Diagrams, vulnerability report, scan outputs, JIRA backlog, RUNBOOK |

## Quick start
```
pip install -r requirements-dev.txt
pytest --cov=app
python -m app.server            # http://127.0.0.1:5055
docker build -t skillup . && docker run -p 8000:8000 skillup
```
See `docs/RUNBOOK.md` for the Jenkins, SonarQube, Trivy and Terraform/AWS steps and `docs/VULNERABILITY_REPORT.md` for the security assessment.

Author: Pasad Neel Bhavin (124BTCS1003)

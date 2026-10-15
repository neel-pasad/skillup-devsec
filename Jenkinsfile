// SkillUp CI/CD pipeline: build -> test -> SonarQube -> Trivy -> Docker -> Terraform -> deploy
// Jenkins prerequisites (see docs/RUNBOOK.md):
//   Plugins : Pipeline, Git, Credentials Binding, SonarQube Scanner, Docker Pipeline, JUnit,
//             AWS Credentials (Amazon Web Services Credentials Binding)
//   Tools   : python3, docker, trivy, terraform, sonar-scanner on the agent (or Jenkins "Tools")
//   Creds   : 'dockerhub-creds' (Username/Password), 'aws-creds' (AWS credentials),
//             'sonar-token' used via the SonarQube server entry named 'sonarqube'
pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds(); timeout(time: 45, unit: 'MINUTES') }
  parameters {
    booleanParam(name: 'DEPLOY_TO_AWS', defaultValue: false, description: 'Run terraform apply and deploy to EC2')
    string(name: 'ALLOWED_SSH_CIDR', defaultValue: '203.0.113.10/32', description: 'Your public IP /32 for SSH')
  }
  environment {
    IMAGE_NAME = 'YOUR_DOCKERHUB_USER/skillup'        // <-- change to your Docker Hub user
    IMAGE_TAG  = "${env.BUILD_NUMBER}"
  }
  stages {
    stage('Checkout') { steps { checkout scm } }

    stage('Install & Unit Test') {
      steps {
        sh '''
          python3 -m venv .venv
          . .venv/bin/activate
          pip install -r requirements-dev.txt
          pytest --cov=app --cov-report=xml:coverage.xml --junitxml=test-results.xml
        '''
      }
      post { always { junit 'test-results.xml' } }
    }

    stage('Static Analysis (Bandit)') {
      steps {
        sh '. .venv/bin/activate && bandit -r app -f txt -o bandit-report.txt || true'
        sh '. .venv/bin/activate && bandit -r app -ll'      // fail on MEDIUM+ findings
      }
    }

    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv('sonarqube') {
          sh 'sonar-scanner'
        }
      }
    }
    stage('Quality Gate') {
      steps { timeout(time: 5, unit: 'MINUTES') { waitForQualityGate abortPipeline: true } }
    }

    stage('Trivy: Dependencies, Secrets, IaC') {
      steps {
        sh 'trivy fs --scanners vuln,secret --severity HIGH,CRITICAL --exit-code 1 --format table -o trivy-fs.txt .'
        sh 'trivy config --severity HIGH,CRITICAL --format table -o trivy-config.txt . || true'
      }
    }

    stage('Docker Build') {
      steps { sh 'docker build -t $IMAGE_NAME:$IMAGE_TAG -t $IMAGE_NAME:latest .' }
    }

    stage('Trivy: Docker Image') {
      steps {
        sh 'trivy image --severity HIGH,CRITICAL --exit-code 1 --format table -o trivy-image.txt $IMAGE_NAME:$IMAGE_TAG'
      }
    }

    stage('Smoke Test Container') {
      steps {
        sh '''
          docker rm -f skillup-ci 2>/dev/null || true
          docker run -d --name skillup-ci -p 8000:8000 $IMAGE_NAME:$IMAGE_TAG
          for i in $(seq 1 15); do curl -fs http://localhost:8000/health && break || sleep 2; done
          curl -fs http://localhost:8000/health | grep '"status":"ok"'
        '''
      }
      post { always { sh 'docker rm -f skillup-ci || true' } }
    }

    stage('Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
          sh '''
            echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
            docker push $IMAGE_NAME:$IMAGE_TAG
            docker push $IMAGE_NAME:latest
            docker logout
          '''
        }
      }
    }

    stage('Terraform: Provision AWS') {
      when { expression { params.DEPLOY_TO_AWS } }
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
          dir('terraform') {
            sh '''
              terraform init -input=false
              terraform validate
              terraform plan -input=false -out=tfplan \
                -var "docker_image=$IMAGE_NAME:$IMAGE_TAG" -var "allowed_ssh_cidr=${ALLOWED_SSH_CIDR}"
              terraform apply -input=false -auto-approve tfplan
              terraform output -raw website_url > ../website_url.txt
            '''
          }
        }
      }
    }

    stage('Post-Deploy Check') {
      when { expression { params.DEPLOY_TO_AWS } }
      steps {
        sh '''
          URL=$(cat website_url.txt)
          for i in $(seq 1 30); do curl -fs "$URL/health" && break || sleep 10; done
          curl -fs "$URL/health" | grep '"status":"ok"'
        '''
      }
    }
  }
  post {
    always { archiveArtifacts artifacts: '*.txt, coverage.xml, test-results.xml', allowEmptyArchive: true }
    success { echo 'Pipeline succeeded' }
    failure { echo 'Pipeline failed: check the stage that turned red (tests, quality gate or a security scan)' }
  }
}

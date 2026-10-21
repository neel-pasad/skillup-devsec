// SkillUp CI/CD pipeline: test -> SonarQube -> Trivy -> Docker -> push to Amazon ECR -> Terraform (Ubuntu EC2)
// Jenkins prerequisites (see docs/RUNBOOK.md, step 7):
//   Plugins : Pipeline, Git, Credentials Binding, SonarQube Scanner, JUnit, AWS Credentials
//   On the Jenkins machine (PATH): python3 + venv, docker, trivy, terraform, aws cli, sonar-scanner
//   Creds   : 'aws-creds' (AWS Credentials: access key + secret), SonarQube server entry named 'sonarqube'
pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds(); timeout(time: 45, unit: 'MINUTES') }
  parameters {
    booleanParam(name: 'RUN_TERRAFORM', defaultValue: false, description: 'Create the Ubuntu EC2 server with Terraform')
    string(name: 'ALLOWED_SSH_CIDR', defaultValue: '203.0.113.10/32', description: 'Your public IP /32 for SSH')
    string(name: 'KEY_NAME', defaultValue: 'skillup-key', description: 'Existing EC2 key pair name')
  }
  environment {
    PATH       = "/opt/homebrew/bin:/usr/local/bin:${env.PATH}"   // so Jenkins finds brew-installed tools on a Mac
    AWS_REGION = 'ap-south-1'
    ECR_REPO   = 'skillup'
    IMAGE_NAME = 'skillup'
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

    stage('SonarQube Analysis (SAST)') {
      steps { withSonarQubeEnv('sonarqube') { sh 'sonar-scanner' } }
    }
    stage('Quality Gate') {
      steps { timeout(time: 5, unit: 'MINUTES') { waitForQualityGate abortPipeline: true } }
    }

    stage('Trivy: Dependencies, Secrets, IaC') {
      steps {
        sh 'trivy fs --scanners vuln,secret --severity HIGH,CRITICAL --exit-code 1 --format table -o trivy-fs-report.txt .'
        sh 'trivy config --severity HIGH,CRITICAL --format table -o trivy-config-report.txt . || true'
      }
    }

    stage('Docker Build') {
      steps { sh 'docker build -t $IMAGE_NAME:$IMAGE_TAG .' }
    }

    stage('Trivy: Docker Image Scan') {
      steps {
        sh 'trivy image --format json -o trivy-image-report.json $IMAGE_NAME:$IMAGE_TAG'
        sh 'trivy image --severity HIGH,CRITICAL --exit-code 1 --format table -o trivy-image-report.txt $IMAGE_NAME:$IMAGE_TAG'
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

    stage('Push Image to Amazon ECR') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
          sh '''
            ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
            REGISTRY=$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
            aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION >/dev/null 2>&1 || \
              aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION --image-scanning-configuration scanOnPush=true
            aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY
            docker tag $IMAGE_NAME:$IMAGE_TAG $REGISTRY/$ECR_REPO:$IMAGE_TAG
            docker push $REGISTRY/$ECR_REPO:$IMAGE_TAG
            echo "$REGISTRY/$ECR_REPO:$IMAGE_TAG" > ecr-image.txt
          '''
        }
      }
    }

    stage('Terraform: Create Ubuntu EC2') {
      when { expression { params.RUN_TERRAFORM } }
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
          dir('terraform') {
            sh '''
              terraform init -input=false
              terraform validate
              terraform plan -input=false -out=tfplan -var "allowed_ssh_cidr=${ALLOWED_SSH_CIDR}" -var "key_name=${KEY_NAME}"
              terraform apply -input=false -auto-approve tfplan
              terraform output
            '''
          }
        }
      }
    }
  }
  post {
    always { archiveArtifacts artifacts: '*.txt, *.json, coverage.xml, test-results.xml', allowEmptyArchive: true }
    success { echo 'Pipeline succeeded. Next: SSH to the EC2 and run the image with the docker CLI (RUNBOOK step 9).' }
    failure { echo 'Pipeline failed: check the red stage (tests, quality gate or a security scan)' }
  }
}

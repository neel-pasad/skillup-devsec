
pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    timeout(time: 45, unit: 'MINUTES')
  }

  parameters {
    booleanParam(
      name: 'RUN_TERRAFORM',
      defaultValue: false,
      description: 'Create the Ubuntu EC2 server with Terraform'
    )
    string(
      name: 'ALLOWED_SSH_CIDR',
      defaultValue: '203.0.113.10/32',
      description: 'Your public IP /32 for SSH'
    )
    string(
      name: 'KEY_NAME',
      defaultValue: 'skillup-key',
      description: 'Existing EC2 key pair name'
    )
  }

  environment {
    PATH       = "/opt/homebrew/bin:/usr/local/bin:${env.PATH}"
    AWS_REGION = 'ap-south-1'
    ECR_REPO   = 'skillup'
    IMAGE_NAME = 'skillup'
    IMAGE_TAG  = "${env.BUILD_NUMBER}"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        sh '''
          echo "Repository workspace:"
          pwd
          echo "Application files:"
          ls -la skillup-devsecops
          test -f skillup-devsecops/requirements-dev.txt
          test -f skillup-devsecops/Dockerfile
        '''
      }
    }

    stage('Install & Unit Test') {
      steps {
        dir('skillup-devsecops') {
          sh '''
            python3 -m venv .venv
            . .venv/bin/activate
            python3 -m pip install --upgrade pip
            python3 -m pip install -r requirements-dev.txt
            pytest --cov=app --cov-report=xml:coverage.xml --junitxml=test-results.xml
          '''
        }
      }
      post {
        always {
          script {
            if (fileExists('skillup-devsecops/test-results.xml')) {
              junit 'skillup-devsecops/test-results.xml'
            } else {
              echo 'JUnit report not created because pytest did not produce one.'
            }
          }
        }
      }
    }

    stage('Static Analysis (Bandit)') {
      steps {
        dir('skillup-devsecops') {
          sh '''
            . .venv/bin/activate
            bandit -r app -f txt -o bandit-report.txt || true
            bandit -r app -ll
          '''
        }
      }
    }

    stage('SonarQube Analysis (SAST)') {
      steps {
        dir('skillup-devsecops') {
          withSonarQubeEnv('sonarqube') {
            sh 'sonar-scanner'
          }
        }
      }
    }

    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    stage('Trivy: Dependencies, Secrets, IaC') {
      steps {
        dir('skillup-devsecops') {
          sh '''
            trivy fs \
              --scanners vuln,secret \
              --severity HIGH,CRITICAL \
              --exit-code 1 \
              --format table \
              -o trivy-fs-report.txt .

            trivy config \
              --severity HIGH,CRITICAL \
              --format table \
              -o trivy-config-report.txt . || true
          '''
        }
      }
    }

    stage('Docker Build') {
      steps {
        dir('skillup-devsecops') {
          sh '''
            docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
          '''
        }
      }
    }

    stage('Trivy: Docker Image Scan') {
      steps {
        dir('skillup-devsecops') {
          sh '''
            trivy image \
              --format json \
              -o trivy-image-report.json \
              "$IMAGE_NAME:$IMAGE_TAG"

            trivy image \
              --severity HIGH,CRITICAL \
              --exit-code 1 \
              --format table \
              -o trivy-image-report.txt \
              "$IMAGE_NAME:$IMAGE_TAG"
          '''
        }
      }
    }

    stage('Smoke Test Container') {
      steps {
        sh '''
          docker rm -f skillup-ci 2>/dev/null || true

          docker run -d \
            --name skillup-ci \
            -p 8000:8000 \
            "$IMAGE_NAME:$IMAGE_TAG"

          success=0
          for i in $(seq 1 15); do
            if curl -fsS http://localhost:8000/health; then
              success=1
              break
            fi
            sleep 2
          done

          if [ "$success" -ne 1 ]; then
            echo "Health endpoint did not become available."
            docker logs skillup-ci || true
            exit 1
          fi

          curl -fsS http://localhost:8000/health |
            grep -E '"status"[[:space:]]*:[[:space:]]*"ok"'
        '''
      }
      post {
        always {
          sh 'docker rm -f skillup-ci || true'
        }
      }
    }

    stage('Push Image to Amazon ECR') {
      steps {
        withCredentials([
          [$class: 'AmazonWebServicesCredentialsBinding',
           credentialsId: 'aws-creds']
        ]) {
          sh '''
            set -eu

            ACCOUNT=$(aws sts get-caller-identity \
              --query Account --output text)

            REGISTRY="$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"

            aws ecr describe-repositories \
              --repository-names "$ECR_REPO" \
              --region "$AWS_REGION" >/dev/null 2>&1 || \
            aws ecr create-repository \
              --repository-name "$ECR_REPO" \
              --region "$AWS_REGION" \
              --image-scanning-configuration scanOnPush=true

            aws ecr get-login-password --region "$AWS_REGION" |
              docker login --username AWS --password-stdin "$REGISTRY"

            docker tag "$IMAGE_NAME:$IMAGE_TAG" \
              "$REGISTRY/$ECR_REPO:$IMAGE_TAG"

            docker push "$REGISTRY/$ECR_REPO:$IMAGE_TAG"

            echo "$REGISTRY/$ECR_REPO:$IMAGE_TAG" \
              > skillup-devsecops/ecr-image.txt
          '''
        }
      }
    }

    stage('Terraform: Create Ubuntu EC2') {
      when {
        expression { params.RUN_TERRAFORM }
      }
      steps {
        withCredentials([
          [$class: 'AmazonWebServicesCredentialsBinding',
           credentialsId: 'aws-creds']
        ]) {
          dir('skillup-devsecops/terraform') {
            sh '''
              set -eu
              terraform init -input=false
              terraform validate

              terraform plan \
                -input=false \
                -out=tfplan \
                -var "allowed_ssh_cidr=${ALLOWED_SSH_CIDR}" \
                -var "key_name=${KEY_NAME}"

              terraform apply -input=false -auto-approve tfplan
              terraform output
            '''
          }
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts(
        artifacts: 'skillup-devsecops/*.txt, skillup-devsecops/*.json, skillup-devsecops/*.xml, skillup-devsecops/*.html, skillup-devsecops/terraform/*.tfplan',
        allowEmptyArchive: true
      )
    }

    success {
      echo 'Pipeline succeeded. Check the archived reports and deployment outputs.'
    }

    failure {
      echo 'Pipeline failed. Review the first failed stage in Console Output.'
    }
  }
}

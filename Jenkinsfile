pipeline {
    agent any

    environment {
        IMAGE_NAME = "sumannath/yt-shorts-bot"
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/sumannath/YouTubeShortsBot.git',
                    branch: 'master'
            }
        }

        stage('Build and Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', 'docker-hub-creds') {
                        def customImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
                        customImage.push()
                        customImage.push("latest")
                    }
                }
            }
        }

        stage('Deploy to Minikube') {
            agent {
                docker {
                    image 'bitnami/kubectl:latest'
                    args '-v /var/jenkins_home/.kube:/root/.kube'
                }
            }
            steps {
                sh '''
                echo "Deploying to Minikube..."
                kubectl set image deployment/yt-shorts-bot yt-shorts-bot=${IMAGE_NAME}:${IMAGE_TAG} --record || \
                kubectl apply -f k8s/deployment.yaml
                kubectl rollout status deployment/yt-shorts-bot
                '''
            }
        }
    }

    post {
        always {
            echo 'Cleaning up unused Docker resources...'
            sh 'docker image prune -f || true'
        }
    }
}

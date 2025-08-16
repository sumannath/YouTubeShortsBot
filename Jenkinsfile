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
                        // Build image
                        def customImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}")

                        // Push with build number
                        customImage.push()

                        // Also push as 'latest'
                        customImage.push("latest")
                    }
                }
            }
        }

        stage('Deploy to Minikube') {
            steps {
                sh '''
                echo "Deploying to Minikube..."
                kubectl set image deployment/yt-shorts-bot yt-shorts-bot=${IMAGE_NAME}:${IMAGE_TAG} --record || \
                kubectl apply -f k8s/deployment.yaml
                kubectl rollout status deployment/yt-shorts-bot
                '''
            }
    }

    post {
        always {
            echo 'Cleaning up unused Docker resources...'
            sh 'docker image prune -f || true'
        }
    }
}

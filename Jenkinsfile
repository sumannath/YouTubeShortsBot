pipeline {
    agent any
    environment {
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout'){
           steps {
                git url: 'https://github.com/sumannath/YouTubeShortsBot.git',
                branch: 'master'
           }
        }

        stage('Build Docker'){
            steps{
                script{
                    sh '''
                    echo 'Build Docker Image'
                    docker build -t sumannath/yt-shorts-bot:${BUILD_NUMBER} .
                    '''
                }
            }
        }

        stage('Push the artifacts'){
           steps{
                script{
                    sh '''
                    echo 'Push to Repo'
                    docker push sumannath/yt-shorts-bot:${BUILD_NUMBER}
                    '''
                }
            }
        }
    }
}
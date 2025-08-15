pipeline {
    agent any
    environment {
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout'){
           steps {
                url: 'https://github.com/sumannath/YouTubeShortsBot.git',
                branch: 'master'
           }
        }
    }
}
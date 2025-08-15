pipeline {
    agent any
    environment {
        IMAGE_TAG = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout'){
           steps {
                git credentialsId: 'f87a34a8-0e09-45e7-b9cf-6dc68feac670',
                url: 'https://github.com/iam-veeramalla/cicd-end-to-end',
                branch: 'main'
           }
        }
    }
}
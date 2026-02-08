pipeline {
    agent any

    environment {
        PARTNER_NUM = '0'
        // Ovde definišeš environment varijable koje su ti u .env fajlu
        AUTH = credentials('oneshield-login') 
        USERNAMEE = '${env.AUTH_USR}'
        PASSWORD = '${env.AUTH_PSW}'
    }

    stages {
        stage('Checkout') {
            steps {
                // Jenkins će automatski povući kod sa GitHub-a
                checkout scm
            }
        }

        stage('Setup Environment') {
            steps {
                bat """
                python -m venv venv
                call venv\\Scripts\\activate
                pip install -r requirements.txt
                playwright install chromium
                """
            }
        }

        stage('Run Tests') {
            steps {
                bat """
                call venv\\Scripts\\activate
                if exist allure-results (rd /s /q allure-results)
                pytest --alluredir=allure-results
                """
            }
        }
    }

    post {
        always {
            // Generisanje Allure reporta
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        }
    }
}
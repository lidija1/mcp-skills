pipeline {
    agent any

    environment {
        PARTNER_NUM = '0'
        // Here you can set any other environment variables you need for your tests
        AUTH = credentials('oneshield-login') 
        USERNAMEE = "${env.AUTH_USR}"
        PASSWORD = "${env.AUTH_PSW}"
    }

    stages {
        stage('Checkout') {
            steps {
                // JenJenkins automatcly check the code from the repository, but you can explicitly define it if needed
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
            // Generating Allure Report
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        }
    }
}
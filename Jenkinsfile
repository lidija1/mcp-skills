pipeline {
    agent any

    parameters {
        string(name: 'BROWSER', defaultValue: 'chromium', description: 'Browser to run the tests on (chromium, firefox, webkit)')
    }

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
                // Run tests and generate Allure results
                // Use the BROWSER parameter to specify the browser to run the tests on
                // Example: Set BROWSER to 'firefox' in Jenkins UI to run tests on Firefox
                bat """
                call venv\\Scripts\\activate
                if exist allure-results (rd /s /q allure-results) // Remove old Allure results if they exist
                pytest %TEST_PATH% --browser=%BROWSER% --alluredir=allure-results // Run tests with the specified browser and save results to Allure directory
                """
            }
        }

        stage('Generate Coverage Report') {
            steps {
                bat """
                call venv\\Scripts\\activate
                pytest --cov=./ --cov-report=html
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
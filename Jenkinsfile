pipeline {
    agent any // Use any available agent to run the pipeline

    environment {
        PARTNER_NUM = '0' // Example environment variable for partner number
        AUTH = credentials('oneshield-login') // Fetch credentials from Jenkins credentials store
        USERNAMEE = "${env.AUTH_USR}" // Username from the credentials
        PASSWORD = "${env.AUTH_PSW}" // Password from the credentials
    }

    parameters {
        string(name: 'TEST_PATH', defaultValue: 'tests/', description: 'Path to the test file or directory to run')
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout the source code from the repository
                checkout scm
            }
        }

        stage('Setup Environment') {
            steps {
                // Set up Python virtual environment and install dependencies
                bat """
                python -m venv venv
                call venv\\Scripts\\activate
                pip install -r requirements.txt
                playwright install chromium // Install Playwright and Chromium browser
                """
            }
        }

        stage('Run Tests') {
            steps {
                // Run tests and generate Allure results
                // Use the TEST_PATH parameter to specify the test file or directory to run
                // Example: Set TEST_PATH to 'tests/test_file.py::test_case_name' in Jenkins UI to run a specific test case
                bat """
                call venv\\Scripts\\activate
                if exist allure-results (rd /s /q allure-results) // Remove old Allure results if they exist
                pytest %TEST_PATH% --alluredir=allure-results // Run tests and save results to Allure directory
                """
            }
        }

        stage('Generate Coverage Report') {
            steps {
                // Generate test coverage report in HTML format
                bat """
                call venv\\Scripts\\activate
                pytest --cov=./ --cov-report=html
                """
            }
        }

        stage('Generate Allure Report') {
            steps {
                // Generate Allure report from test results
                bat """
                call venv\\Scripts\\activate
                allure generate allure-results -o allure-report --clean
                """
            }
        }

        stage('Archive Allure Report') {
            steps {
                // Archive the Allure report for future reference
                archiveArtifacts artifacts: 'allure-report/**', fingerprint: true
            }
        }

        stage('Code Quality Check') {
            steps {
                // Run flake8 for code quality checks
                bat """
                call venv\\Scripts\\activate
                flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                """
            }
        }
    }

    post {
        always {
            // Always generate Allure report after pipeline execution
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        }
    }
}
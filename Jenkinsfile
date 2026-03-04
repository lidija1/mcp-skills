pipeline {
    agent any

    parameters {
        string(name: 'BROWSER', defaultValue: 'chromium', description: 'Browser to run the tests on (chromium, firefox, webkit)')
        string(name: 'TEST_PATH', defaultValue: 'ui/', description: 'Path to the test file or directory to run')
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
                // Set up Python virtual environment and install dependencies
                // Install Playwright and Chromium browser
                // Clean venv to avoid stale packages (e.g., pytest-playwright)
                bat '''
                if exist venv (rd /s /q venv)
                python -m venv venv
                call venv\\Scripts\\activate
                pip install -r requirements.txt
                playwright install chromium
                '''
            }
        }

        stage('Run Tests') {
            steps {
                // Run tests and generate Allure results
                // Use the BROWSER parameter to specify the browser to run the tests on
                // Use the TEST_PATH parameter to specify which tests to run
                // Example: Set BROWSER to 'firefox' in Jenkins UI to run tests on Firefox
                bat '''
                call venv\\Scripts\\activate
                set PYTHONPATH=%CD%
                if exist allure-results (rd /s /q allure-results)
                pytest %TEST_PATH% --browser=%BROWSER% --alluredir=allure-results
                '''
            }
        }

        stage('Generate Coverage Report') {
            steps {
                // Generate test coverage report in HTML format
                bat '''
                call venv\\Scripts\\activate
                set PYTHONPATH=%CD%
                pytest --cov=./ --cov-report=html
                '''
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
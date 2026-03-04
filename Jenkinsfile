pipeline {
    agent any

    parameters {
        string(name: 'BROWSER', defaultValue: 'chromium', description: 'Browser to run the tests on (chromium, firefox, webkit)')
        string(name: 'TEST_PATH', defaultValue: 'ui/', description: 'Path to the test file or directory to run')
    }

    environment {
        PARTNER_NUM = '0'
        DOCKER_IMAGE = "sandbox-playwright:${env.BUILD_NUMBER}"
        CONTAINER_NAME = "sandbox-playwright-tests-${env.BUILD_NUMBER}"
        AUTH = credentials('oneshield-login')
        USERNAMEE = "${env.AUTH_USR}"
        PASSWORD = "${env.AUTH_PSW}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                bat '''
                docker build --no-cache -t %DOCKER_IMAGE% .
                '''
            }
        }

        stage('Run Tests in Docker') {
            steps {
                bat '''
                if exist reports (rd /s /q reports)
                if exist allure-results (rd /s /q allure-results)
                if exist screenshots (rd /s /q screenshots)
                mkdir reports
                mkdir allure-results
                mkdir screenshots
                docker rm -f %CONTAINER_NAME% >nul 2>&1
                docker run --name %CONTAINER_NAME% ^
                  -e PARTNER_NUM=%PARTNER_NUM% ^
                  -e USERNAMEE=%USERNAMEE% ^
                  -e PASSWORD=%PASSWORD% ^
                  -v "%WORKSPACE%\\reports:/app/reports" ^
                  -v "%WORKSPACE%\\allure-results:/app/allure-results" ^
                  -v "%WORKSPACE%\\screenshots:/app/screenshots" ^
                  %DOCKER_IMAGE% pytest %TEST_PATH% --browser=%BROWSER%
                '''
            }
        }
    }

    post {
        always {
            bat '''
            docker rm -f %CONTAINER_NAME% >nul 2>&1
            '''

            archiveArtifacts artifacts: 'reports/**/*, screenshots/**/*', allowEmptyArchive: true
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        }

        cleanup {
            bat '''
            docker rmi %DOCKER_IMAGE% >nul 2>&1
            '''
        }
    }
}
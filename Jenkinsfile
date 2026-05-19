pipeline {
    agent any

    parameters {
        string(name: 'BROWSER', defaultValue: 'chromium', description: 'Browser to run the tests on (chromium, firefox, webkit)')
        string(name: 'TEST_PATH', defaultValue: 'ui/', description: 'Path to the test file or directory to run')
        booleanParam(name: 'FORCE_BUILD', defaultValue: false, description: 'Force rebuild Docker image even if it exists')
        booleanParam(name: 'RUN_LIGHTHOUSE', defaultValue: false, description: 'Run Lighthouse audit after test execution')
        string(name: 'LIGHTHOUSE_TARGET_URL', defaultValue: 'https://example.com', description: 'URL to audit when RUN_LIGHTHOUSE is enabled')
    }

    environment {
        PARTNER_NUM = '0'
        // Use stable image name - only rebuild when needed
        DOCKER_IMAGE = "sandbox-playwright:latest"
        CONTAINER_NAME = "sandbox-playwright-tests-${env.BUILD_NUMBER}"
        AUTH = credentials('oneshield-login')
        USERNAMEE = "${env.AUTH_USR}"
        PASSWORD = "${env.AUTH_PSW}"
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Build Docker Image') {
            when {
                anyOf {
                    // Build if FORCE_BUILD is checked
                    expression { return params.FORCE_BUILD }
                    // Build if image doesn't exist
                    expression {
                        def imageExists = bat(script: 'docker images -q sandbox-playwright:latest', returnStdout: true).trim()
                        return imageExists == ''
                    }
                    // Build if Dockerfile changed (compare hash)
                    expression {
                        def currentHash = bat(script: '@certutil -hashfile Dockerfile MD5 | findstr /v "hash"', returnStdout: true).trim()
                        def storedHash = ''
                        try {
                            storedHash = readFile('.docker_hash').trim()
                        } catch (Exception e) {
                            storedHash = ''
                        }
                        return currentHash != storedHash
                    }
                }
            }
            steps {
                bat '''
                echo Building Docker image...
                docker build -t %DOCKER_IMAGE% .
                '''
                // Save hash for future comparison
                script {
                    def hash = bat(script: '@certutil -hashfile Dockerfile MD5 | findstr /v "hash"', returnStdout: true).trim()
                    writeFile file: '.docker_hash', text: hash
                }
            }
        }

        stage('Skip Build Notice') {
            when {
                allOf {
                    expression { return !params.FORCE_BUILD }
                    expression {
                        def imageExists = bat(script: 'docker images -q sandbox-playwright:latest', returnStdout: true).trim()
                        return imageExists != ''
                    }
                }
            }
            steps {
                echo 'Docker image already exists - skipping build (use FORCE_BUILD to rebuild)'
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

        stage('Run Lighthouse Audit') {
            when {
                expression { return params.RUN_LIGHTHOUSE }
            }
            steps {
                bat '''
                if not exist reports\lighthouse (mkdir reports\lighthouse)
                docker run --rm ^
                  --user 0:0 ^
                  -v "%WORKSPACE%:/workspace" ^
                  -w /workspace ^
                  patrickhulce/lhci-client:0.15.1 ^
                  lhci autorun --config=/workspace/lighthouse/lighthouserc.json --collect.url=%LIGHTHOUSE_TARGET_URL% --collect.numberOfRuns=3 --upload.target=filesystem --upload.outputDir=/workspace/reports/lighthouse
                '''
            }
        }
    }

    post {
        always {
            bat '''
            docker rm -f %CONTAINER_NAME% >nul 2>&1
            '''

            archiveArtifacts artifacts: 'reports/**/*, reports/lighthouse/**/*, screenshots/**/*', allowEmptyArchive: true
            allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        }
        // Image is preserved for reuse - not deleted
        // To force a fresh build, use FORCE_BUILD parameter
    }
}
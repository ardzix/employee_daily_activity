pipeline {

    environment {
        DEPLOY = 'true'
        DOCKER_IMAGE = 'ardzix/employee_activity_tracker'
        DOCKER_REGISTRY_CREDENTIALS = 'ard-dockerhub'
        NAMESPACE = 'employee_activity_tracker'
        STACK_NAME = 'employee_activity_tracker'
        REPLICAS = '1'
        NETWORK_NAME = 'production'
    }

    stages {
        stage('Clean Workspace') {
            steps {
                sh '''
                    find . -mindepth 1 -maxdepth 1 ! -name 'Jenkinsfile' -exec rm -rf {} +
                '''
            }
        }

        stage('Checkout Code') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'github-ardzix', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')]) {
                    sh '''
                        mv Jenkinsfile ../Jenkinsfile.tmp
                        rm -rf ./*
                        rm -rf ./.??*
                        git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/ardzix/employee_daily_activity.git .
                        mv ../Jenkinsfile.tmp Jenkinsfile
                    '''
                }
            }
        }

        stage('Inject Environment Variables and PEM Files') {
            steps {
                withCredentials([
                    file(credentialsId: 'employee-activity-tracker-env', variable: 'ENV_FILE'),
                    string(credentialsId: 'ms-arnatech-storage-access', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'ms-arnatech-storage-secret', variable: 'AWS_SECRET_ACCESS_KEY'),
                    file(credentialsId: 'sso_public_pem', variable: 'PUBLIC_PEM_FILE')
                ]) {
                    sh """
                        cp "${ENV_FILE}" .env.tmp
                        sed -i "s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}|" .env.tmp
                        sed -i "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}|" .env.tmp
                        mv .env.tmp .env
                        cp "${PUBLIC_PEM_FILE}" public.pem
                    """
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:latest", ".")
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKER_REGISTRY_CREDENTIALS) {
                        docker.image("${DOCKER_IMAGE}:latest").push()
                    }
                }
            }
        }

        stage('Deploy to Swarm (VPS - uWSGI Only)') {
            when {
                expression { return env.DEPLOY?.toBoolean() ?: false }
            }
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: 'stag-arnatech-sa-01', keyFileVariable: 'SSH_KEY_FILE')
                ]) {
                    sh '''
                        echo "[INFO] Preparing VPS deployment..."
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@172.105.124.43 "mkdir -p /root/employee_activity_tracker"

                        echo "[INFO] Copying .env and supervisord config to VPS..."
                        scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no .env root@172.105.124.43:/root/employee_activity_tracker/.env
                        scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no supervisord.conf root@172.105.124.43:/root/employee_activity_tracker/supervisord.conf

                        echo "[INFO] Deploying Docker service to Swarm..."
                        ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@172.105.124.43 bash -c '
                            docker swarm init || true
                            docker network create --driver overlay production || true
                            docker service rm employee_activity_tracker || true

                            docker service create --name employee_activity_tracker \
                                --replicas 1 \
                                --network production \
                                --env-file /root/employee_activity_tracker/.env \
                                --mount type=bind,src=/root/employee_activity_tracker/supervisord.conf,dst=/etc/supervisor/conf.d/supervisord.conf,ro=true \
                                ardzix/employee_activity_tracker:latest
                        '
                    '''
                }
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished!'
        }
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
} 

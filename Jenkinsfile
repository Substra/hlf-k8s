pipeline {
  options {
    timestamps ()
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '5'))
    skipDefaultCheckout true
  }

  agent none

  stages {
    stage('Abort previous builds'){
      steps {
        milestone(Integer.parseInt(env.BUILD_ID)-1)
        milestone(Integer.parseInt(env.BUILD_ID))
      }
    }

    stage('Test') {
      agent {
        kubernetes {
          label 'python'
          defaultContainer 'python'
          yamlFile '.cicd/agent-python.yaml'
        }
      }

      steps {
        sh """
          apt update
          apt install -y curl
          mkdir -p /tmp/download
          curl -L https://download.docker.com/linux/static/stable/x86_64/docker-18.06.3-ce.tgz | tar -xz -C /tmp/download
          mv /tmp/download/docker/docker /usr/local/bin/
          apt install -y docker-compose
        """

        dir('substra-chaincode') {
            checkout([
              $class: 'GitSCM',
              branches: [[name: '*/dev']],
              doGenerateSubmoduleConfigurations: false,
              extensions: [],
              submoduleCfg: [],
              userRemoteConfigs: [[credentialsId: 'substra-deploy', url: 'https://github.com/SubstraFoundation/substra-chaincode']]
            ])
        }

        dir("substra-network") {
          checkout scm
          sh "pip install -r python-scripts/requirements.txt"
          sh "./bootstrap.sh"
          sh "python3 python-scripts/start.py --no-backup --fixtures --revoke"
        }

      }

      post {
        always {
          dir("substra-network") {
            sh "python3 python-scripts/stop.py"
          }
        }
      }
    }
  }
}

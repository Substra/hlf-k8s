pipeline {
  options {
    timestamps ()
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '5'))
    skipDefaultCheckout true
    lock('substranetwork')
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

        sh """
          rm -rf /tmp/substra/substra-chaincode
          mkdir -p /tmp/substra/substra-chaincode
          cp -r substra-chaincode/chaincode/* /tmp/substra/substra-chaincode/
        """

        dir("substra-network") {
          checkout scm
          sh "pip install -r python-scripts/requirements.txt"
          sh "./bootstrap.sh"
          sh "export SUBSTRA_PATH=/tmp/substra/"
          sh "python3 python-scripts/start.py --no-backup --fixtures --revoke"
        }

        // Verify that the start.py go well.
        // Todo: improve this part
        sh """
          if [ -f /tmp/substra/data/log/fixtures.fail ]; then echo "Fixture fails" && exit 1; fi
          if [ -f /tmp/substra/data/log/revoke.fail ]; then echo "Revoke fails" && exit 1; fi
          if [ -f /tmp/substra/data/log/run-chu-nantes.fail ]; then cat /tmp/substra/data/log/run-chu-nantes.fail && exit 1; fi
          if [ -f /tmp/substra/data/log/run-owkin.fail ]; then cat /tmp/substra/data/log/run-owkin.log && exit 1; fi
          if [ -f /tmp/substra/data/log/setup-chu-nantes.fail ]; then cat /tmp/substra/data/log/setup-chu-nantes.log && exit 1; fi
          if [ -f /tmp/substra/data/log/setup-orderer.fail ]; then cat /tmp/substra/data/log/setup-orderer.log && exit 1; fi
          if [ -f /tmp/substra/data/log/setup-owkin.fail ]; then cat /tmp/substra/data/log/setup-owkin.log && exit 1; fi
        """

      }

      post {
        always {
          dir("substra-network") {
            sh "export SUBSTRA_PATH=/tmp/substra/"
            sh "python3 python-scripts/stop.py"
          }
          sh "rm -rf /tmp/substra/* "
        }
      }
    }
  }
}

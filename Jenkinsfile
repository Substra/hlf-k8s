pipeline {
  options {
    timestamps ()
    timeout(time: 1, unit: 'HOURS')
    buildDiscarder(logRotator(numToKeepStr: '5'))
    skipDefaultCheckout true
    lock('substranetwork')
  }

  parameters {
    string(name: 'CHAINCODE', defaultValue: 'dev', description: 'chaincode branch')
    string(name: 'BACKEND', defaultValue: 'dev', description: 'substrabac branch')
    string(name: 'CLI', defaultValue: 'dev', description: 'substra-cli branch')
    string(name: 'DOC', defaultValue: 'master', description: 'substra-doc branch')

    }

  agent none

  stages {
    stage('Abort previous builds'){
      steps {
        milestone(Integer.parseInt(env.BUILD_ID)-1)
        milestone(Integer.parseInt(env.BUILD_ID))
      }
    }

    stage('Test substra network and chaincode') {
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
              branches: [[name: "*/${params.CHAINCODE}"]],
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
          sh "python3 python-scripts/start.py --no-backup --fixtures --revoke --query"
        }
      }

      post {
        always {
          dir("substra-network") {
            sh "export SUBSTRA_PATH=/tmp/substra/"
            sh "python3 python-scripts/stop.py"
          }

          // Verify that the start.py go well.
          // Todo: improve this part
          sh """
            if [ -f /tmp/substra/data/log/fixtures.fail ]; then cat /tmp/substra/data/log/fixtures.log; fi
            if [ -f /tmp/substra/data/log/revoke.fail ]; then cat /tmp/substra/data/log/revoke.log; fi
            if [ -f /tmp/substra/data/log/run-chu-nantes.fail ]; then cat /tmp/substra/data/log/run-chu-nantes.log; fi
            if [ -f /tmp/substra/data/log/run-owkin.fail ]; then cat /tmp/substra/data/log/run-owkin.log; fi
            if [ -f /tmp/substra/data/log/setup-chu-nantes.fail ]; then cat /tmp/substra/data/log/setup-chu-nantes.log; fi
            if [ -f /tmp/substra/data/log/setup-orderer.fail ]; then cat /tmp/substra/data/log/setup-orderer.log; fi
            if [ -f /tmp/substra/data/log/setup-owkin.fail ]; then cat /tmp/substra/data/log/setup-owkin.log; fi
          """

          sh "rm -rf /tmp/substra/* "
        }
      }
    }

    stage('Test substra-network, chaincode and substra backend') {
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
              branches: [[name: "*/${params.CHAINCODE}"]],
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

        dir('substra-cli') {
            checkout([
              $class: 'GitSCM',
              branches: [[name: "*/${params.CLI}"]],
              doGenerateSubmoduleConfigurations: false,
              extensions: [],
              submoduleCfg: [],
              userRemoteConfigs: [[credentialsId: 'substra-deploy', url: 'https://github.com/SubstraFoundation/substra-cli']]
            ])
        }

        sh """
          pip install substra-cli/
          pip install termcolor pandas sklearn

        """

        dir("substra-network") {
          checkout scm
          sh "pip install -r python-scripts/requirements.txt"
          sh "./bootstrap.sh"
          sh "export SUBSTRA_PATH=/tmp/substra/"
          sh "python3 python-scripts/start.py --no-backup"
        }

        dir('substrabac') {
            checkout([
              $class: 'GitSCM',
              branches: [[name: "*/${params.BACKEND}"]],
              doGenerateSubmoduleConfigurations: false,
              extensions: [],
              submoduleCfg: [],
              userRemoteConfigs: [[credentialsId: 'substra-deploy', url: 'https://github.com/SubstraFoundation/substrabac']]
            ])

            sh """
              sh ./build-docker-images.sh
              export SUBSTRA_PATH=/tmp/substra/
              cd ./docker && python3 start.py -d --no-backup
              sleep 120
              echo \$MY_HOST_IP owkin.substrabac >> /etc/hosts
              echo \$MY_HOST_IP chunantes.substrabac >> /etc/hosts
              cd ../ && python3 populate.py

            """
        }

        dir('substra-doc') {
            checkout([
              $class: 'GitSCM',
              branches: [[name: "*/${params.DOC}"]],
              doGenerateSubmoduleConfigurations: false,
              extensions: [],
              submoduleCfg: [],
              userRemoteConfigs: [[credentialsId: 'substra-deploy', url: 'https://github.com/SubstraFoundation/substra-doc']]
            ])

            sh """
              cd examples/titanic
              python3 -m pip install -r scripts/requirements.txt
              python3 scripts/generate_data_samples.py
              python3 scripts/add_dataset_objective.py
              cd ../compute_plan
              python3 scripts/add_compute_plan.py
            """
        }

      }

      post {
        always {

          dir('substrabac') {
            sh "cd ./docker; python3 stop.py"
          }

          dir("substra-network") {
            sh "export SUBSTRA_PATH=/tmp/substra/"
            sh "python3 python-scripts/stop.py"
          }

          // Verify that the start.py go well.
          // Todo: improve this part
          sh """
            if [ -f /tmp/substra/data/log/fixtures.fail ]; then cat /tmp/substra/data/log/fixtures.log; fi
            if [ -f /tmp/substra/data/log/revoke.fail ]; then cat /tmp/substra/data/log/revoke.log; fi
            if [ -f /tmp/substra/data/log/run-chu-nantes.fail ]; then cat /tmp/substra/data/log/run-chu-nantes.log; fi
            if [ -f /tmp/substra/data/log/run-owkin.fail ]; then cat /tmp/substra/data/log/run-owkin.log; fi
            if [ -f /tmp/substra/data/log/setup-chu-nantes.fail ]; then cat /tmp/substra/data/log/setup-chu-nantes.log; fi
            if [ -f /tmp/substra/data/log/setup-orderer.fail ]; then cat /tmp/substra/data/log/setup-orderer.log; fi
            if [ -f /tmp/substra/data/log/setup-owkin.fail ]; then cat /tmp/substra/data/log/setup-owkin.log; fi
          """

          sh "rm -rf /tmp/substra/* "
        }
      }
    }

  }
}

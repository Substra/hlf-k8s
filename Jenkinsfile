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

    stage('Prepare substra volume'){
      agent {
        kubernetes {
          label 'kubectl'
          defaultContainer 'kubectl'
          yaml """
            apiVersion: v1
            kind: Pod
            spec:
              containers:
              - name: kubectl
                image: roffe/kubectl
                command: [cat]
                tty: true
            """
        }
      }

      steps {
        checkout scm
        sh "kubectl delete -f .cicd/substra-volume-claim.yaml"
        sh "kubectl apply -f .cicd/substra-volume-claim.yaml"
      }
    }

    stage('Test') {
      agent {
        kubernetes {
          label 'python'
          defaultContainer 'python'
          yaml """
            apiVersion: v1
            kind: Pod
            spec:
              containers:
              - name: python
                image: python:3.7
                command: [cat]
                tty: true
                volumeMounts:
                - { name: susbtra, mountPath: /substra }
                - { name: docker, mountPath: /var/run/docker.sock }
              volumes:
                - name: substra
                  persistentVolumeClaim:
                    claimName: substra-data
                - name: docker
                  hostPath: { path: /var/run/docker.sock, type: File }
            """
        }
      }

      steps {
        sh "apt update"
        sh "apt install curl && mkdir -p /tmp/download && curl -L https://download.docker.com/linux/static/stable/x86_64/docker-18.06.3-ce.tgz | tar -xz -C /tmp/download && mv /tmp/download/docker/docker /usr/local/bin/"
        sh "apt install docker-compose"

        dir('substra-chaincode') {
            checkout([$class: 'GitSCM', branches: [[name: '*/dev']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'substra-deploy', url: 'https://github.com/SubstraFoundation/substra-chaincode']]])
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
          sh "python3 python-scripts/stop.py"
        }
      }
    }
  }
}

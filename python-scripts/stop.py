import os
from subprocess import call
from util import remove_chaincode_docker_containers, remove_chaincode_docker_images

dir_path = os.path.dirname(os.path.realpath(__file__))


def stop():
    print('stopping container')
    remove_chaincode_docker_containers()
    remove_chaincode_docker_images()
    call(['docker-compose', '-f', os.path.join(dir_path, '../docker-compose.yaml'), 'down', '--remove-orphans'])


if __name__ == "__main__":
    stop()

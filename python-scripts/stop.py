import os
import glob
from subprocess import call
from utils.common_utils import remove_chaincode_docker_containers, remove_chaincode_docker_images

dir_path = os.path.dirname(os.path.realpath(__file__))

from start import SUBSTRA_PATH


def stop():
    print('stopping container')
    remove_chaincode_docker_containers()
    remove_chaincode_docker_images()

    # Stop all
    docker_compose_paths = glob.glob(os.path.join(SUBSTRA_PATH, 'dockerfiles/*.yaml'))

    for docker_compose_path in docker_compose_paths:
        call(['docker-compose', '-f', docker_compose_path, 'down', '--remove-orphans'])


if __name__ == "__main__":
    stop()

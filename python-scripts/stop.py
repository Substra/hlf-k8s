# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        call(['docker-compose', '-f', docker_compose_path, 'kill'])
        call(['docker-compose', '-f', docker_compose_path, 'down', '--remove-orphans'])


if __name__ == "__main__":
    stop()

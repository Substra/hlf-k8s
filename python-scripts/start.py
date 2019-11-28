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
import json
import argparse

from yaml import load, FullLoader

from subprocess import call, check_call

from utils.common_utils import (dowait, create_directory, remove_chaincode_docker_images,
                                remove_chaincode_docker_containers)
from utils.config_utils import (create_configtx, create_ca_server_config, create_ca_client_config, create_peer_config,
                                create_orderer_config, create_substra_backend_config)
from utils.docker_utils import (generate_docker_compose_org, generate_docker_compose_orderer, generate_fixtures_docker,
                                generate_revoke_docker, generate_query_docker)

dir_path = os.path.dirname(os.path.realpath(__file__))

SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')
SUBSTRA_NETWORK = 'net_substra'


def remove_all_docker():

    # Stop all
    docker_compose_paths = glob.glob(os.path.join(SUBSTRA_PATH, 'dockerfiles/*.yaml'))

    down_cmds = []

    for docker_compose_path in docker_compose_paths:
        with open(docker_compose_path) as dockercomposefile:
            dockercomposeconf = load(dockercomposefile, Loader=FullLoader)

            if 'services' in dockercomposeconf:
                services = list(dockercomposeconf['services'].keys())
                # Force removal (quicker)
                if services:
                    call(['docker', 'rm', '-f'] + services)

            down_cmds.append(['docker-compose', '-f', docker_compose_path, 'kill'])
            down_cmds.append(['docker-compose', '-f', docker_compose_path, 'down', '--remove-orphans'])

    for cmd in down_cmds:
        call(cmd)

    remove_chaincode_docker_containers()
    remove_chaincode_docker_images()

    call(['docker', 'network', 'remove', SUBSTRA_NETWORK])


def intern_stop(docker_compose):
    print('stopping container', flush=True)
    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'True'
    check_call(['docker-compose', '-f', docker_compose, '--project-directory', dir_path, 'kill'])
    check_call(['docker-compose', '-f', docker_compose, '--project-directory', dir_path, 'down'])
    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'


def start(conf, docker_compose):
    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'True'
    project_directory = os.path.join(dir_path, os.pardir)
    print('Start docker-compose', flush=True)

    # RCA
    print('Start Root Certificate Authority', flush=True)
    services = [name for name, _ in docker_compose['substra_services']['rca']]
    check_call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d'] +
               services)

    check_call(['docker', 'ps', '-a', '--format', 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}',
                '--filter', 'label=substra'])

    # Setup
    print(conf['misc']['setup_success_file'])
    if not os.path.exists(conf['misc']['setup_success_file']):
        print('Launch setup')
        check_call(['docker-compose', '-f', docker_compose['path'], '--project-directory',
                   project_directory, 'up', '-d', 'setup'])
        check_call(['docker', 'ps', '-a', '--format', 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}',
                    '--filter', 'label=substra'])
        # Wait for the setup container to complete
        success = dowait('the \'setup\' container to finish registering identities and other artifacts',
                         90,
                         conf['misc']['setup_logfile'],
                         [conf['misc']['setup_success_file']])
        if not success:
            exit(1)
    else:
        print('Setup not launched because %s exists.' % conf['misc']['setup_success_file'])

    # SVC
    services = [name for name, _ in docker_compose['substra_services']['svc']]
    print('Start services %s' % services, flush=True)
    check_call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d',
               '--no-deps'] + services)

    if 'orgs' in conf:
        peers_orgs_files = [peer['tls']['clientCert']
                            for org in conf['orgs']
                            for peer in org['peers']]
        success = dowait('the docker \'peer\' containers to complete',
                         30, None,
                         peers_orgs_files)

        if not success:
            exit(1)

    # Run
    with open(docker_compose['path']) as dockercomposefile:
        dockercomposeconf = load(dockercomposefile, Loader=FullLoader)
        has_run = 'run' in dockercomposeconf['services'].keys()

    if has_run and 'run_success_file' in conf['misc']:
        if not os.path.exists(conf['misc']['run_success_file']):
            check_call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d',
                       '--no-deps', 'run'])

            # Wait for the run container to start and complete
            success = dowait('the docker \'run\' container to run and complete',
                             160, conf['misc']['run_logfile'],
                             [conf['misc']['run_success_file']])
            if not success:
                exit(1)
        else:
            print(f"Run not launched because {conf['misc']['run_success_file']} exists.")

    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'


def substra_org(org, orderer=None):
    org_name = org['name']

    print(f'Prepare Node : {org_name}')
    create_directory(f"{SUBSTRA_PATH}/data/orgs/{org_name}")
    create_directory(f"{SUBSTRA_PATH}/conf/{org_name}")

    # CA files
    create_ca_server_config(org)
    create_ca_client_config(org)

    # Configtx file
    config_filepath = os.path.join(org['misc']['configtx-config-path'], 'configtx.yaml')
    create_configtx(org, config_filepath, raft=True)

    # Org Config files
    if org['type'] == 'client':
        create_peer_config(org)
        # create_fabric_ca_peer_config(org)
        # Docker-compose for org
        docker_compose = generate_docker_compose_org(org, orderer, SUBSTRA_PATH, SUBSTRA_NETWORK)
        intern_stop(docker_compose['path'])
        start(org, docker_compose)

    # Orderer Config files
    if org['type'] == 'orderer':
        create_peer_config(org)
        create_orderer_config(org)
        docker_compose = generate_docker_compose_orderer(org,
                                                         SUBSTRA_PATH,
                                                         SUBSTRA_NETWORK)
        intern_stop(docker_compose['path'])
        start(org, docker_compose)


def substra_network(org):

    # Stop all
    docker_compose_paths = glob.glob(os.path.join(SUBSTRA_PATH, 'dockerfiles/*.yaml'))

    # Remove all
    remove_all_docker()

    for docker_compose_path in docker_compose_paths:
        intern_stop(docker_compose_path)

    # Create Network
    check_call(['docker', 'network', 'create', SUBSTRA_NETWORK])

    for orderer in [x for x in orgs if x['type'] == 'orderer']:
        substra_org(orderer)
    else:
        # Prepare each org
        for org in [x for x in orgs if x['type'] == 'client']:
            substra_org(org, orderer)
            # substra-backend
            create_directory(f"{SUBSTRA_PATH}/dryrun/{org['name']}")
            create_substra_backend_config(org)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', nargs='?', type=str, action='store', default='',
                        help="JSON config file to be used")
    parser.add_argument('--no-backup', action='store_true', default=False,
                        help="Remove backup binded volume. Launch from scratch")
    parser.add_argument('-f', '--fixtures', action='store_true', default=False,
                        help="Add fixtures")
    parser.add_argument('-r', '--revoke', action='store_true', default=False,
                        help="Revoke user and test querying")
    parser.add_argument('-q', '--query', action='store_true', default=False,
                        help="Query with user")
    args = vars(parser.parse_args())

    # Stop all docker
    remove_all_docker()

    if args['no_backup']:
        # create directory with correct rights
        check_call(['rm', '-rf', f'{SUBSTRA_PATH}/data'])
        check_call(['rm', '-rf', f'{SUBSTRA_PATH}/conf'])
        check_call(['rm', '-rf', f'{SUBSTRA_PATH}/backup'])
        check_call(['rm', '-rf', f'{SUBSTRA_PATH}/dryrun'])
        check_call(['rm', '-rf', f'{SUBSTRA_PATH}/dockerfiles'])

    create_directory(f'{SUBSTRA_PATH}/data/log')
    create_directory(f'{SUBSTRA_PATH}/conf/')
    create_directory(f'{SUBSTRA_PATH}/conf/config')
    create_directory(f'{SUBSTRA_PATH}/dryrun/')
    create_directory(f'{SUBSTRA_PATH}/dockerfiles/')

    if not glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json'):
        # Global configuration
        if args['config']:
            check_call(['python3', args['config']])
        else:
            check_call(['python3', os.path.join(dir_path, 'conf/2orgs.py')])

    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    print('  Organizations :', flush=True)
    for org in orgs:
        print('   -', org['name'], flush=True)
    print('', flush=True)

    substra_network(orgs)

    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'True'

    if args['fixtures']:
        suffix = 's' if len(orgs) - 1 > 1 else ''
        fixtures_path = f'fixtures{len(orgs) - 1}org{suffix}.py'
        docker_compose_path = generate_fixtures_docker(SUBSTRA_PATH, fixtures_path, SUBSTRA_NETWORK)
        project_directory = os.path.join(dir_path, os.pardir)
        check_call(['docker-compose', '-f', docker_compose_path, '--project-directory', project_directory, 'up', '-d',
                   '--no-deps', 'fixtures'])
        # Wait for the run container to start and complete
        success = dowait('the docker fixtures container to run and complete',
                         160, f'{SUBSTRA_PATH}/data/log/fixtures.log',
                         [f'{SUBSTRA_PATH}/data/log/fixtures.successful'])

        if not success:
            os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'
            call(['touch', f'{SUBSTRA_PATH}/data/log/fixtures.fail'])
            exit(1)

    if args['query']:
        docker_compose_path = generate_query_docker(SUBSTRA_PATH, SUBSTRA_NETWORK)
        project_directory = os.path.join(dir_path, os.pardir)
        check_call(['docker-compose', '-f', docker_compose_path, '--project-directory', project_directory, 'up', '-d',
                   '--no-deps', 'query'])
        # Wait for the run container to start and complete
        success = dowait('the docker query container to run and complete',
                         160, f'{SUBSTRA_PATH}/data/log/query.log',
                         [f'{SUBSTRA_PATH}/data/log/query.successful'])

        if not success:
            os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'
            call(['touch', f'{SUBSTRA_PATH}/data/log/query.fail'])
            exit(1)

    if args['revoke']:
        docker_compose_path = generate_revoke_docker(SUBSTRA_PATH, SUBSTRA_NETWORK)
        project_directory = os.path.join(dir_path, os.pardir)
        check_call(['docker-compose', '-f', docker_compose_path, '--project-directory', project_directory, 'up', '-d',
                   '--no-deps', 'revoke'])
        # Wait for the run container to start and complete
        success = dowait('the docker revoke container to run and complete',
                         160, f'{SUBSTRA_PATH}/data/log/revoke.log',
                         [f'{SUBSTRA_PATH}/data/log/revoke.successful'])

        if not success:
            os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'
            call(['touch', f'{SUBSTRA_PATH}/data/log/revoke.fail'])
            exit(1)

    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'

import os
import glob
import json
import argparse

from subprocess import call

from utils.common_utils import dowait, create_directory, remove_chaincode_docker_images, remove_chaincode_docker_containers
from utils.config_utils import (create_configtx, create_ca_server_config, create_ca_client_config, create_core_peer_config, create_orderer_config,
                                create_fabric_ca_peer_config, create_fabric_ca_orderer_config, create_substrabac_config)
from utils.docker_utils import generate_docker_compose_org, generate_docker_compose_orderer

dir_path = os.path.dirname(os.path.realpath(__file__))

SUBSTRA_PATH = '/substra'
SUBSTRA_NETWORK = 'net_substra'


def stop(docker_compose):
    print('stopping container', flush=True)
    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'True'
    call(['docker-compose', '-f', docker_compose, '--project-directory', dir_path, 'down'])
    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'
    # remove_chaincode_docker_containers()
    # remove_chaincode_docker_images()


def start(conf, docker_compose):
    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'True'
    project_directory = os.path.join(dir_path, '../')
    print('Start docker-compose', flush=True)

    # RCA
    print('Start Root Certificate Authority', flush=True)
    services = [name for name, _ in docker_compose['substra_services']['rca']]
    call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d'] + services)
    call(['docker', 'ps', '-a'])

    # Setup
    print(conf['misc']['setup_success_file'])
    if not os.path.exists(conf['misc']['setup_success_file']):
        print('Launch setup')
        call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d', 'setup'])
        call(['docker', 'ps', '-a'])
        # Wait for the setup container to complete
        dowait('the \'setup\' container to finish registering identities and other artifacts',
               90,
               conf['misc']['setup_logfile'],
               [conf['misc']['setup_success_file']])
    else:
        print('Setup not launched because %s exists.' % conf['misc']['setup_success_file'])

    # SVC
    services = [name for name, _ in docker_compose['substra_services']['svc']]
    print('Start services %s' % services, flush=True)
    call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d', '--no-deps'] + services)

    if 'orgs' in conf:
        peers_orgs_files = [peer['tls']['clientCert']
                            for org in conf['orgs']
                            for peer in org['peers']]
        dowait('the docker \'peer\' containers to complete',
               30, None,
               peers_orgs_files)

    # Run
    if 'run_success_file' in conf['misc']:
        if not os.path.exists(conf['misc']['run_success_file']):
            call(['docker-compose', '-f', docker_compose['path'], '--project-directory', project_directory, 'up', '-d', '--no-deps', 'run'])

            # Wait for the run container to start and complete
            dowait('the docker \'run\' container to run and complete',
                   160, conf['misc']['run_logfile'],
                   [conf['misc']['run_success_file']])
        else:
            print('Run not launched because %s exists.' % conf['misc']['run_success_file'])

    os.environ['COMPOSE_IGNORE_ORPHANS'] = 'False'


def substra_orderer(conf):

    # Orderer config file
    conf_orderer = {'misc': dict(conf['misc']),
                    'orderers': conf['orderers']}
    del conf_orderer['misc']['run_logfile']
    del conf_orderer['misc']['run_sumfile']
    del conf_orderer['misc']['run_success_file']
    del conf_orderer['misc']['run_fail_file']
    json.dump(conf_orderer, open(f'{SUBSTRA_PATH}/conf/conf-orderer.json', 'w'))

    # Orderer directories
    print('Prepare Orderers : ', [orderer['name'] for orderer in conf_orderer['orderers']])
    for orderer in conf_orderer['orderers']:
        create_directory(f"{SUBSTRA_PATH}/data/orgs/{orderer['name']}")
        create_directory(f"{SUBSTRA_PATH}/conf/{orderer['name']}")

    # CA files
    create_ca_server_config(conf_orderer['orderers'])
    create_ca_client_config(conf_orderer['orderers'])

    # Configtx file
    config_filepath = conf_orderer['misc']['configtx-config-path']
    config_filepath = config_filepath.replace('configtx.yaml', 'configtx-orderer.yaml')
    create_configtx(conf_orderer, config_filepath)

    # Orderer Config files
    create_orderer_config(conf_orderer)
    create_fabric_ca_orderer_config(conf_orderer)

    # Docker-compose for orderer
    orderer_docker_compose = generate_docker_compose_orderer(conf_orderer['orderers'][0], SUBSTRA_PATH, SUBSTRA_NETWORK)
    stop(orderer_docker_compose['path'])
    start(conf_orderer, orderer_docker_compose)


def substra_org(conf, org):

    org_name = org['name']

    # Org config file
    conf_org = {'misc': dict(conf['misc']),
                'orderers': conf['orderers'],
                'orgs': [org]}
    conf_org['misc']['setup_logfile'] = f'/substra/data/log/setup-{org_name}.log',
    conf_org['misc']['setup_success_file'] = f'/substra/data/log/setup-{org_name}.successful'
    conf_org['misc']['run_logfile'] = f'/substra/data/log/run-{org_name}.log'
    conf_org['misc']['run_sumfile'] = f'/substra/data/log/run-{org_name}.sum'
    conf_org['misc']['run_success_file'] = f'/substra/data/log/run-{org_name}.successful'
    conf_org['misc']['run_fail_file'] = f'/substra/data/log/run-{org_name}.fail'
    json.dump(conf_org, open(f'{SUBSTRA_PATH}/conf/conf-{org_name}.json', 'w'))

    print(f'Prepare Node : {org_name}')
    create_directory(f"{SUBSTRA_PATH}/dryrun/{org_name}")
    create_directory(f"{SUBSTRA_PATH}/data/orgs/{org_name}")
    create_directory(f"{SUBSTRA_PATH}/conf/{org_name}")

    # CA files
    create_ca_server_config([org])
    create_ca_client_config([org])

    # Configtx file
    config_filepath = conf_org['misc']['configtx-config-path']
    config_filepath = config_filepath.replace('configtx.yaml', f'configtx-{org_name}.yaml')
    create_configtx(conf_org, config_filepath)

    # Org Config files
    create_core_peer_config(conf_org)
    create_fabric_ca_peer_config(conf_org)
    create_substrabac_config(conf_org)

    org_docker_compose = generate_docker_compose_org(org, SUBSTRA_PATH, SUBSTRA_NETWORK)
    stop(org_docker_compose['path'])
    start(conf_org, org_docker_compose)


def substra_network(conf):

    # Stop all
    docker_compose_paths = os.path.join(SUBSTRA_PATH, 'dockerfiles')
    docker_compose_paths = glob.glob(os.path.join(SUBSTRA_PATH, 'dockerfiles/*.yaml'))

    for docker_compose_path in docker_compose_paths:
        stop(docker_compose_path)

    # Remove all
    remove_all()

    # Create Network
    call(['docker', 'network', 'create', SUBSTRA_NETWORK])
    substra_orderer(conf)

    # Prepare each org
    for org in conf['orgs']:
        substra_org(conf, org)


def remove_all():

    # Hardcoded removal
    call(['docker', 'rm', '-f', 'rca-orderer', 'rca-owkin', 'rca-chu-nantes',
          'setup', 'orderer1-orderer', 'peer1-owkin', 'peer2-owkin', 'peer1-chu-nantes',
          'peer2-chu-nantes', 'run', 'run-owkin', 'run-chu-nantes', 'setup-owkin', 'setup-chu-nantes'])

    remove_chaincode_docker_containers()
    remove_chaincode_docker_images()

    call(['docker', 'network', 'remove', SUBSTRA_NETWORK])


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', nargs='?', type=str, action='store', default='',
                        help="JSON config file to be used")
    parser.add_argument('--no-backup', action='store_true', default=False,
                        help="Remove backup binded volume. Launch from scratch")
    args = vars(parser.parse_args())

    # Global configuration
    conf_path = f'{SUBSTRA_PATH}/conf/conf.json'

    # Stop all docker
    remove_all()

    if args['no_backup']:
        # create directory with correct rights
        call(['rm', '-rf', f'{SUBSTRA_PATH}/data'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/conf'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/backup'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/dryrun'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/dockerfiles'])

    create_directory(f'{SUBSTRA_PATH}/data/log')
    create_directory(f'{SUBSTRA_PATH}/conf/')
    create_directory(f'{SUBSTRA_PATH}/dryrun/')
    create_directory(f'{SUBSTRA_PATH}/dockerfiles/')

    if not os.path.exists(conf_path):
        if args['config']:
            call(['python3', args['config']])
        else:
            call(['python3', os.path.join(dir_path, 'conf/2orgs.py')])
    else:
        print(f'Use existing configuration in {SUBSTRA_PATH}/conf/conf.json', flush=True)

    conf = json.load(open(conf_path, 'r'))

    print('Build substra-network for : ', flush=True)
    print('  Orderer :')
    for orderer in conf['orderers']:
        print('   -', orderer['name'], flush=True)

    print('  Organizations :', flush=True)
    for org in conf['orgs']:
        print('   -', org['name'], flush=True)
    print('', flush=True)

    substra_network(conf)

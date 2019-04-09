import os
import json
import argparse

from subprocess import call
from util import dowait, create_directory, remove_chaincode_docker_images, remove_chaincode_docker_containers
from start import create_ca_server_config, create_ca_client_config, create_core_peer_config, create_orderer_config, create_fabric_ca_peer_config, create_fabric_ca_orderer_config, create_substrabac_config
from docker_utils import generate_docker_compose_org, generate_docker_compose_orderer
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

dir_path = os.path.dirname(os.path.realpath(__file__))

LOGGING_LEVEL = ['critical', 'error', 'warning', 'notice', 'info', 'debug']
SUBSTRA_PATH = '/substra'
SUBSTRA_NETWORK = 'net_substra'


def create_configtx(conf, filename):
    stream = open(os.path.join(dir_path, '../templates/configtx.yaml'), 'r')
    yaml_data = load(stream, Loader=Loader)

    # override template here

    if 'orderers' in conf:
        yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Addresses'] = [f"{x['host']}:{x['port']}" for x in conf['orderers']]

        orderers = [{
            'Name': x['name'],
            'ID': x['msp_id'],
            'MSPDir': f"{x['users']['admin']['home']}/msp",
        } for x in conf['orderers']]
    else:
        orderers = []

    if 'orgs' in conf:
        orgs = [{
            'Name': x['name'],
            'ID': x['msp_id'],
            'MSPDir': f"{x['users']['admin']['home']}/msp",
            'AnchorPeers': [{
                'Host': peer['host'],
                'Port': peer['port']
            } for peer in x['peers'] if peer['anchor']]
        } for x in conf['orgs']]
    else:
        orgs = []

    yaml_data['Organizations'] = orderers + orgs

    yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Organizations'] = orderers
    yaml_data['Profiles']['OrgsOrdererGenesis']['Consortiums']['SampleConsortium']['Organizations'] = orgs
    yaml_data['Profiles']['OrgsChannel']['Application']['Organizations'] = orgs

    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def stop(docker_compose):
    print('stopping container', flush=True)

    call(['docker-compose', '-f', docker_compose, '--project-directory', dir_path, 'down'])

    remove_chaincode_docker_containers()
    remove_chaincode_docker_images()


def launch(docker_compose, conf):

    dir_dc_path = os.path.join(dir_path, '../')
    print('start docker-compose', flush=True)
    services = [name for name, _ in docker_compose['substra_services']['rca']]

    print(conf['misc']['setup_success_file'])
    if not os.path.exists(conf['misc']['setup_success_file']):
        services += ['setup']

    call(['docker-compose', '-f', docker_compose['path'], '--project-directory', dir_dc_path, 'up', '-d'] + services)
    call(['docker', 'ps', '-a'])

    # Wait for the setup container to complete
    dowait('the \'setup\' container to finish registering identities, creating the genesis block and other artifacts',
           90, conf['misc']['setup_logfile'],
           [conf['misc']['setup_success_file']])

    services = [name for name, _ in docker_compose['substra_services']['svc']]
    call(['docker-compose', '-f', docker_compose['path'], '--project-directory', dir_dc_path, 'up', '-d', '--no-deps'] + services)

    if 'orgs' in conf:
        peers_orgs_files = []
        for org in conf['orgs']:
            peers_orgs_files = [peer['tls']['clientCert'] for peer in org['peers']]

        dowait('the docker \'peer\' containers to complete',
               30, None,
               peers_orgs_files)

    if 'run_success_file' in conf['misc']:

        if not os.path.exists(conf['misc']['run_success_file']):
            call(['docker-compose', '-f', docker_compose['path'], '--project-directory', dir_dc_path, 'up', '-d', '--no-deps', 'run'])

        # Wait for the run container to start and complete
        dowait('the docker \'run\' container to run and complete',
               160, conf['misc']['run_logfile'],
               [conf['misc']['run_success_file']])


def start(conf, conf_path):

    conf_init = {'misc': dict(conf['misc']),
                 'orderers': conf['orderers']}

    del conf_init['misc']['run_logfile']
    del conf_init['misc']['run_sumfile']
    del conf_init['misc']['run_success_file']
    del conf_init['misc']['run_fail_file']

    json.dump(conf_init, open(f'{SUBSTRA_PATH}/conf/conf-init.json', 'w'))

    # Create Network
    call(['docker', 'network', 'create', SUBSTRA_NETWORK])

    # Prepare orderers and network
    print('Prepare Orderers : ', [orderer['name'] for orderer in conf_init['orderers']])

    for org in conf_init['orderers']:
        create_directory(f"{SUBSTRA_PATH}/data/orgs/{org['name']}")
        create_directory(f"{SUBSTRA_PATH}/conf/{org['name']}")

    print('\tCreating ca server/client files for each orderer', flush=True)
    create_ca_server_config(conf_init['orderers'])
    create_ca_client_config(conf_init['orderers'])

    print(f'\tCreating configtx with orderers of the {SUBSTRA_NETWORK} network', flush=True)
    config_filepath = conf_init['misc']['configtx-config-path'].replace('configtx.yaml',
                                                                        'configtx-init.yaml')

    # We should do an update of orderer configtx instead of providing one org for consortium
    # create_configtx(conf_init,
    #                 config_filepath)
    create_configtx({**conf_init, **{'orgs': conf['orgs'][0:1]}},
                    config_filepath)

    print('\tCreating config for each orderer', flush=True)
    create_orderer_config(conf_init)
    create_fabric_ca_orderer_config(conf_init)
    print(f'\tGenerate docker-compose file for "{conf_init["orderers"][0]["name"]}"\n')
    dc_init = generate_docker_compose_orderer(conf_init['orderers'][0], SUBSTRA_PATH, SUBSTRA_NETWORK)
    stop(dc_init['path'])
    launch(dc_init, conf_init)

    # Prepare each org
    orgs_inplace = []
    for org in conf['orgs']:

        conf_org = {'misc': dict(conf['misc']),
                    'orderers': conf['orderers'],
                    'orgs': [org]}

        conf_org['misc']['setup_logfile'] = f'/substra/data/log/setup-{org["name"]}.log',
        conf_org['misc']['setup_success_file'] = f'/substra/data/log/setup-{org["name"]}.successful'
        conf_org['misc']['run_logfile'] = f'/substra/data/log/run-{org["name"]}.log'
        conf_org['misc']['run_sumfile'] = f'/substra/data/log/run-{org["name"]}.sum'
        conf_org['misc']['run_success_file'] = f'/substra/data/log/run-{org["name"]}.successful'
        conf_org['misc']['run_fail_file'] = f'/substra/data/log/run-{org["name"]}.fail'

        json.dump(conf_org, open(f'{SUBSTRA_PATH}/conf/conf-{org["name"]}.json', 'w'))

        org = conf_org['orgs'][0]
        org_name = org['name']
        print(f'Prepare Node : {org_name}')

        create_directory(f"{SUBSTRA_PATH}/dryrun/{org['name']}")
        create_directory(f"{SUBSTRA_PATH}/data/orgs/{org['name']}")
        create_directory(f"{SUBSTRA_PATH}/conf/{org['name']}")

        print('\tCreating ca server/client files', flush=True)
        create_ca_server_config([org])
        create_ca_client_config([org])

        print(f'\tCreating configtx for {org_name} node of the {SUBSTRA_NETWORK} network', flush=True)
        config_filepath = conf_org['misc']['configtx-config-path'].replace('configtx.yaml',
                                                                           f'configtx-{org_name}.yaml')
        create_configtx(conf_org,
                        config_filepath)

        print(f'\tCreating config for node {org_name}', flush=True)
        create_core_peer_config(conf_org)
        create_fabric_ca_peer_config(conf_org)
        create_substrabac_config(conf_org)

        print(f'\tGenerate docker-compose file for "{org_name}"\n')
        dc_org = generate_docker_compose_org(org, SUBSTRA_PATH, SUBSTRA_NETWORK)
        stop(dc_org['path'])
        launch(dc_org, conf_org)


def remove_all():
    # Hardcoded removal
    call(['docker', 'rm', '-f', 'rca-orderer', 'rca-owkin', 'rca-chu-nantes', 'setup', 'orderer1-orderer',
          'peer1-owkin', 'peer2-owkin', 'peer1-chu-nantes', 'peer2-chu-nantes', 'run', 'fixtures', 'queryUser',
          'revoke', 'run-owkin', 'run-chu-nantes', 'setup-owkin', 'setup-chu-nantes'])

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

    conf_path = f'{SUBSTRA_PATH}/conf/conf.json'

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

    start(conf, conf_path)

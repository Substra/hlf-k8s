import os
import json
import argparse

from subprocess import call
from .common_utils import dowait, create_directory, remove_chaincode_docker_images, remove_chaincode_docker_containers

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

dir_path = os.path.dirname(os.path.realpath(__file__))

SUBSTRA_PATH = '/substra'


def create_ca_server_config(orgs):
    # For each org, create a config file from template
    for org in orgs:
        stream = open(os.path.join(dir_path, '../../templates/fabric-ca-server-config.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['tls']['certfile'] = org['tls']['certfile']

        yaml_data['ca']['name'] = org['ca']['name']
        yaml_data['ca']['certfile'] = org['ca']['certfile']
        # yaml_data['ca']['keyfile'] = org['ca']['keyfile']

        yaml_data['csr']['cn'] = org['csr']['cn']
        yaml_data['csr']['hosts'] += org['csr']['hosts']

        yaml_data['registry']['identities'][0]['name'] = org['users']['bootstrap_admin']['name']
        yaml_data['registry']['identities'][0]['pass'] = org['users']['bootstrap_admin']['pass']

        filename = org['ca-server-config-path']
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_ca_client_config(orgs):
    # For each org, create a config file from template
    for org in orgs:
        stream = open(os.path.join(dir_path, '../../templates/fabric-ca-client-config.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        # https://hyperledger-fabric-ca.readthedocs.io/en/release-1.2/users-guide.html#enabling-tls
        yaml_data['tls']['certfiles'] = org['ca']['certfile']

        yaml_data['caname'] = org['ca']['name']

        yaml_data['csr']['cn'] = org['csr']['cn']
        yaml_data['csr']['hosts'] += org['csr']['hosts']

        yaml_data['url'] = org['ca']['url']

        filename = org['ca-client-config-path']
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_ca(conf):
    print('Creating ca server/client files for each orderer', flush=True)
    create_ca_server_config(conf['orderers'])
    create_ca_client_config(conf['orderers'])

    print('Creating ca server/client files for each org', flush=True)
    create_ca_server_config(conf['orgs'])
    create_ca_client_config(conf['orgs'])


def create_configtx(conf, filename=None):

    if filename is None:
        filename = conf['misc']['configtx-config-path']

    stream = open(os.path.join(dir_path, '../../templates/configtx.yaml'), 'r')
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


def create_core_peer_config(conf):
    for org in conf['orgs']:
        for peer in org['peers']:
            stream = open(os.path.join(dir_path, '../../templates/core.yaml'), 'r')
            yaml_data = load(stream, Loader=Loader)

            # override template here

            yaml_data['peer']['id'] = peer['host']
            yaml_data['peer']['address'] = f"{peer['host']}:{peer['port']}"
            yaml_data['peer']['localMspId'] = org['msp_id']
            yaml_data['peer']['mspConfigPath'] = org['core']['docker']['msp_config_path']

            yaml_data['peer']['tls']['cert']['file'] = peer['tls']['serverCert']
            yaml_data['peer']['tls']['key']['file'] = peer['tls']['serverKey']
            yaml_data['peer']['tls']['clientCert']['file'] = peer['tls']['clientCert']
            yaml_data['peer']['tls']['clientKey']['file'] = peer['tls']['clientKey']
            yaml_data['peer']['tls']['enabled'] = 'true'
            # the same as peer['tls']['serverCa'] but this one is inside the container
            yaml_data['peer']['tls']['rootcert']['file'] = org['ca']['certfile']
            # passing this to true triggers a SSLV3_ALERT_BAD_CERTIFICATE when querying
            # from the py sdk if peer clientCert/clientKey is not set correctly
            yaml_data['peer']['tls']['clientAuthRequired'] = 'true'
            yaml_data['peer']['tls']['clientRootCAs'] = [org['ca']['certfile']]

            yaml_data['peer']['gossip']['useLeaderElection'] = 'true'
            yaml_data['peer']['gossip']['orgLeader'] = 'false'
            yaml_data['peer']['gossip']['externalEndpoint'] = f"{peer['host']}:{peer['port']}"
            yaml_data['peer']['gossip']['skipHandshake'] = 'true'

            yaml_data['vm']['endpoint'] = 'unix:///host/var/run/docker.sock'
            yaml_data['vm']['docker']['hostConfig']['NetworkMode'] = 'net_substra'

            create_directory(peer['docker_core_dir'])
            filename = f"{peer['docker_core_dir']}/core.yaml"
            with open(filename, 'w+') as f:
                f.write(dump(yaml_data, default_flow_style=False))


def create_orderer_config(conf):
    for orderer in conf['orderers']:
        stream = open(os.path.join(dir_path, '../../templates/orderer.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['General']['TLS']['Certificate'] = orderer['tls']['cert']
        yaml_data['General']['TLS']['PrivateKey'] = orderer['tls']['key']
        yaml_data['General']['TLS']['Enabled'] = 'true'
        # passing this to true triggers a SSLV3_ALERT_BAD_CERTIFICATE when querying
        # from the py sdk if peer clientCert/clientKey is not set correctly
        yaml_data['General']['TLS']['ClientAuthRequired'] = 'true'
        yaml_data['General']['TLS']['RootCAs'] = [orderer['ca']['certfile']]
        yaml_data['General']['TLS']['ClientRootCAs'] = [orderer['ca']['certfile']]

        yaml_data['General']['ListenAddress'] = '0.0.0.0'
        yaml_data['General']['GenesisMethod'] = 'file'
        yaml_data['General']['GenesisFile'] = conf['misc']['genesis_bloc_file']
        yaml_data['General']['LocalMSPID'] = orderer['msp_id']
        yaml_data['General']['LocalMSPDir'] = orderer['local_msp_dir']

        yaml_data['Debug']['BroadcastTraceDir'] = orderer['broadcast_dir']

        filename = orderer['config-path']
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))

        stream = open(os.path.join(dir_path, '../../templates/core.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here

        yaml_data['peer']['id'] = orderer['host']
        yaml_data['peer']['address'] = f"{orderer['host']}:{orderer['port']}"
        yaml_data['peer']['localMspId'] = orderer['msp_id']
        yaml_data['peer']['mspConfigPath'] = orderer['admin_home'] + '/msp'

        yaml_data['peer']['tls']['cert']['file'] = orderer['tls']['cert']
        yaml_data['peer']['tls']['key']['file'] = orderer['tls']['key']
        yaml_data['peer']['tls']['clientCert']['file'] = orderer['tls']['clientCert']
        yaml_data['peer']['tls']['clientKey']['file'] = orderer['tls']['clientKey']
        yaml_data['peer']['tls']['enabled'] = 'true'
        # the same as peer['tls']['serverCa'] but this one is inside the container
        yaml_data['peer']['tls']['rootcert']['file'] = orderer['ca']['certfile']
        # passing this to true triggers a SSLV3_ALERT_BAD_CERTIFICATE when querying
        # from the py sdk if peer clientCert/clientKey is not set correctly
        yaml_data['peer']['tls']['clientAuthRequired'] = 'true'
        yaml_data['peer']['tls']['clientRootCAs'] = [orderer['ca']['certfile']]

        yaml_data['peer']['gossip']['useLeaderElection'] = 'true'
        yaml_data['peer']['gossip']['orgLeader'] = 'false'
        yaml_data['peer']['gossip']['externalEndpoint'] = f"{orderer['host']}:{orderer['port']}"
        yaml_data['peer']['gossip']['skipHandshake'] = 'true'

        yaml_data['vm']['endpoint'] = 'unix:///host/var/run/docker.sock'
        yaml_data['vm']['docker']['hostConfig']['NetworkMode'] = 'net_substra'

        yaml_data['logging']['level'] = LOGGING_LEVEL[4]  # info, needed for substrabac

        filename = f"/substra/conf/{orderer['name']}/core.yaml"
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_fabric_ca_peer_config(conf):
    for org in conf['orgs']:
        peers = org['peers']
        for peer in peers:
            filename = f"{SUBSTRA_PATH}/conf/{org['name']}/{peer['name']}/conf.json"

            # select what need peer conf
            peer_conf = {}
            for k, v in org.items():
                if k in ('users', 'peers', 'ca', 'core'):
                    if k == 'peers':
                        peer_conf['peer'] = [x for x in v if x['name'] == peer['name']][0]
                    elif k == 'users':
                        peer_conf[k] = {k: v for k, v in v.items() if k == 'admin'}
                    else:
                        peer_conf[k] = v
            json.dump(peer_conf, open(filename, 'w+'))


def create_fabric_ca_orderer_config(conf):
    for orderer in conf['orderers']:
        filename = f"{SUBSTRA_PATH}/conf/{orderer['name']}/conf.json"
        orderer_conf = {}
        for k, v in orderer.items():
            if k in ('users', 'ca', 'tls', 'home', 'local_msp_dir', 'host', 'core', 'broadcast_dir'):
                if k == 'users':
                    orderer_conf[k] = {k: v for k, v in v.items() if k == 'admin'}
                else:
                    orderer_conf[k] = v

        orderer_conf.update({'misc': conf['misc']})
        json.dump(orderer_conf, open(filename, 'w+'))


def create_substrabac_config(conf):
    orderer = conf['orderers'][0]
    for org in conf['orgs']:
        dir_path = f"{SUBSTRA_PATH}/conf/{org['name']}/substrabac"
        create_directory(dir_path)

        filename = f"{SUBSTRA_PATH}/conf/{org['name']}/substrabac/conf.json"
        # select what need substrabac conf
        peer = org['peers'][0]
        res = {
            'name': org['name'],
            'signcert': org['users']['user']['home'] + '/msp/signcerts/cert.pem',
            'core_peer_mspconfigpath': org['users']['user']['home'] + '/msp',
            'channel_name': conf['misc']['channel_name'],
            'chaincode_name': conf['misc']['chaincode_name'],
            'peer': {
                'name': peer['name'],
                'host': peer['host'],
                'port': peer['host_port'],
                'docker_port': peer['port'],
                'docker_core_dir': peer['docker_core_dir'],
                'clientKey': peer['tls']['clientKey'],
                'clientCert': peer['tls']['clientCert'],
            },
            'orderer': {
                'name': orderer['name'],
                'host': orderer['host'],
                'port': orderer['port'],
                'ca': orderer['ca']['certfile'],
            }
        }
        json.dump(res, open(filename, 'w+'))


def start(conf, conf_path, fixtures):
    create_ca(conf)
    create_configtx(conf)
    create_core_peer_config(conf)
    create_orderer_config(conf)
    create_fabric_ca_peer_config(conf)
    create_fabric_ca_orderer_config(conf)
    create_substrabac_config(conf)

    print('Generate docker-compose file\n')
    docker_compose = generate_docker_compose_file(conf, conf_path)

    stop(docker_compose)

    print('start docker-compose', flush=True)
    services = [name for name, _ in docker_compose['substra_services']['rca']]

    if not os.path.exists(conf['misc']['setup_success_file']):
        services += ['setup']

    call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--remove-orphans'] + services)
    call(['docker', 'ps', '-a'])

    # Wait for the setup container to complete
    dowait('the \'setup\' container to finish registering identities, creating the genesis block and other artifacts',
           90, conf['misc']['setup_logfile'],
           [conf['misc']['setup_success_file']])

    services = [name for name, _ in docker_compose['substra_services']['svc']]
    call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps'] + services)

    peers_orgs_files = []
    for org in conf['orgs']:
        peers_orgs_files = [peer['tls']['clientCert'] for peer in org['peers']]

    dowait('the docker \'peer\' containers to complete',
           30, None,
           peers_orgs_files)

    if not os.path.exists(conf['misc']['run_success_file']):
        call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'run'])

    # Wait for the run container to start and complete
    dowait('the docker \'run\' container to run and complete',
           160, conf['misc']['run_logfile'],
           [conf['misc']['run_success_file']])

    if fixtures:
        # Load Fixtures
        call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'fixtures'])

        # Wait for the run container to start and complete
        dowait('the docker \'fixtures\' container to run and complete',
               160, conf['misc']['fixtures_logfile'],
               [conf['misc']['fixtures_success_file']])

        # Query with an user MSP
        call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'queryUser'])

        # Revoke User
        call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'revoke'])


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', nargs='?', type=str, action='store', default='',
                        help="JSON config file to be used")
    parser.add_argument('-f', '--fixtures', action='store_true', default=False,
                        help="Load fixtures")
    parser.add_argument('--no-backup', action='store_true', default=False,
                        help="Remove backup binded volume. Launch from scratch")
    args = vars(parser.parse_args())

    conf_path = f'{SUBSTRA_PATH}/conf/conf.json'

    if args['no_backup']:
        # create directory with correct rights
        call(['rm', '-rf', f'{SUBSTRA_PATH}/data'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/conf'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/backup'])
        call(['rm', '-rf', f'{SUBSTRA_PATH}/dryrun'])

    create_directory(f'{SUBSTRA_PATH}/data/log')
    create_directory(f'{SUBSTRA_PATH}/conf/')
    create_directory(f'{SUBSTRA_PATH}/dryrun/')

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

    for org in conf['orgs']:
        create_directory(f"{SUBSTRA_PATH}/dryrun/{org['name']}")

    for org in conf['orgs'] + conf['orderers']:
        create_directory(f"{SUBSTRA_PATH}/data/orgs/{org['name']}")
        create_directory(f"{SUBSTRA_PATH}/conf/{org['name']}")

    start(conf, conf_path, args['fixtures'])

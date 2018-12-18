import os
import json
import argparse

from subprocess import call
from util import dowait, create_directory, remove_chaincode_docker_images, remove_chaincode_docker_containers

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

dir_path = os.path.dirname(os.path.realpath(__file__))

LOGGING_LEVEL = ['critical', 'error', 'warning', 'notice', 'info', 'debug']


def create_ca_server_config(orgs):
    # For each org, create a config file from template
    for org in orgs:
        stream = open(os.path.join(dir_path, '../templates/fabric-ca-server-config.yaml'), 'r')
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
        stream = open(os.path.join(dir_path, '../templates/fabric-ca-client-config.yaml'), 'r')
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


def create_configtx(conf):
    print('Creating configtx of the substra network', flush=True)
    stream = open(os.path.join(dir_path, '../templates/configtx.yaml'), 'r')
    yaml_data = load(stream, Loader=Loader)

    # override template here

    yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Addresses'] = ['%(host)s:%(port)s' % {
        'host': x['host'],
        'port': x['port']
    } for x in conf['orderers']]

    orderers = [{
        'Name': x['name'],
        'ID': x['msp_id'],
        'MSPDir': x['users']['admin']['home'] + '/msp',
    } for x in conf['orderers']]

    orgs = [{
        'Name': x['name'],
        'ID': x['msp_id'],
        'MSPDir': x['users']['admin']['home'] + '/msp',
        'AnchorPeers': [{
            'Host': peer['host'],
            'Port': peer['port']
        } for peer in x['peers'] if peer['anchor']]
    } for x in conf['orgs']]
    yaml_data['Organizations'] = orderers + orgs

    yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Organizations'] = orderers
    yaml_data['Profiles']['OrgsOrdererGenesis']['Consortiums']['SampleConsortium']['Organizations'] = orgs
    yaml_data['Profiles']['OrgsChannel']['Application']['Organizations'] = orgs

    filename = conf['misc']['configtx-config-path']
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_core_peer_config(conf):
    for org in conf['orgs']:
        for peer in org['peers']:
            stream = open(os.path.join(dir_path, '../templates/core.yaml'), 'r')
            yaml_data = load(stream, Loader=Loader)

            # override template here

            yaml_data['peer']['id'] = peer['host']
            yaml_data['peer']['address'] = '%(host)s:%(port)s' % {'host': peer['host'], 'port': peer['port']}
            yaml_data['peer']['localMspId'] = org['msp_id']
            yaml_data['peer']['mspConfigPath'] = org['core']['docker']['msp_config_path']

            yaml_data['peer']['tls']['cert']['file'] = org['core']['docker']['peer_home'] + '/tls/' + \
                                                       org['core']['tls']['cert']
            yaml_data['peer']['tls']['key']['file'] = org['core']['docker']['peer_home'] + '/tls/' + org['core']['tls'][
                'key']
            yaml_data['peer']['tls']['clientCert']['file'] = peer['tls']['clientCert']
            yaml_data['peer']['tls']['clientKey']['file'] = peer['tls']['clientKey']
            yaml_data['peer']['tls']['enabled'] = 'true'
            yaml_data['peer']['tls']['rootcert']['file'] = org['ca']['certfile']
            yaml_data['peer']['tls']['clientAuthRequired'] = 'true'
            yaml_data['peer']['tls']['clientRootCAs'] = [org['ca']['certfile']]

            yaml_data['peer']['gossip']['useLeaderElection'] = 'true'
            yaml_data['peer']['gossip']['orgLeader'] = 'false'
            yaml_data['peer']['gossip']['externalEndpoint'] = peer['host'] + ':' + str(peer['port'])
            yaml_data['peer']['gossip']['skipHandshake'] = 'true'

            yaml_data['vm']['endpoint'] = 'unix:///host/var/run/docker.sock'
            yaml_data['vm']['docker']['hostConfig']['NetworkMode'] = 'net_substra'

            yaml_data['logging']['level'] = LOGGING_LEVEL[4]  # info, needed for substrabac

            create_directory(peer['docker_core_dir'])
            filename = '%(dir)s/core.yaml' % {'dir': peer['docker_core_dir']}
            with open(filename, 'w+') as f:
                f.write(dump(yaml_data, default_flow_style=False))


def create_orderer_config(conf):
    for orderer in conf['orderers']:
        stream = open(os.path.join(dir_path, '../templates/orderer.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['General']['TLS']['Certificate'] = orderer['home'] + '/tls/' + orderer['tls']['cert']
        yaml_data['General']['TLS']['PrivateKey'] = orderer['home'] + '/tls/' + orderer['tls']['key']
        yaml_data['General']['TLS']['Enabled'] = 'true'
        yaml_data['General']['TLS']['ClientAuthRequired'] = 'true'
        yaml_data['General']['TLS']['RootCAs'] = [orderer['tls']['certfile']]
        yaml_data['General']['TLS']['ClientRootCAs'] = [orderer['tls']['certfile']]

        yaml_data['General']['ListenAddress'] = '0.0.0.0'
        yaml_data['General']['GenesisMethod'] = 'file'
        yaml_data['General']['GenesisFile'] = conf['misc']['genesis_bloc_file']
        yaml_data['General']['LocalMSPID'] = orderer['msp_id']
        yaml_data['General']['LocalMSPDir'] = orderer['local_msp_dir']
        yaml_data['General']['LogLevel'] = LOGGING_LEVEL[4]  # info, needed for substrabac

        yaml_data['Debug']['BroadcastTraceDir'] = orderer['broadcast_dir']

        filename = org['config-path']
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def generate_docker_compose_file(conf, conf_path):
    try:
        from ruamel import yaml
    except ImportError:
        import yaml

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': 'setup',
                                                  'image': 'substra/fabric-ca-tools',
                                                  'command': '/bin/bash -c "python3 /scripts/setup.py 2>&1 | tee /substra/data/log/setup.log"',
                                                  'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server',
                                                                  'FABRIC_CFG_PATH=/substra/data'],
                                                  'volumes': ['/substra/data:/substra/data',
                                                              './python-scripts:/scripts',
                                                              '%s:%s' % (conf_path, conf_path)],
                                                  'networks': ['substra'],
                                                  'depends_on': []},

                                        'run': {'container_name': 'run',
                                                'image': 'substra/fabric-ca-tools',
                                                'command': '/bin/bash -c "sleep 3;python3 /scripts/run.py 2>&1 | tee /substra/data/log/run.log"',
                                                'environment': ['GOPATH=/opt/gopath'],
                                                'volumes': ['/var/run/docker.sock:/var/run/docker.sock',
                                                            '/substra/data:/substra/data',
                                                            '/substra/conf:/substra/conf',
                                                            './python-scripts:/scripts',
                                                            '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'
                                                            ],
                                                'networks': ['substra'],
                                                'depends_on': []},
                                        },
                      'substra_test': {
                          'fixtures': {'container_name': 'fixtures',
                                       'image': 'substra/fabric-ca-tools',
                                       'command': '/bin/bash -c "python3 /scripts/%s 2>&1 | tee /substra/data/log/fixtures.log"' %
                                                  conf['misc']['fixtures_path'],
                                       'environment': ['GOPATH=/opt/gopath'],
                                       'volumes': ['/substra/data:/substra/data',
                                                   '/substra/conf:/substra/conf',
                                                   './python-scripts:/scripts',
                                                   '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                       'networks': ['substra'],
                                       'depends_on': ['run']},
                          'queryUser': {'container_name': 'queryUser',
                                        'image': 'substra/fabric-ca-tools',
                                        'command': '/bin/bash -c "python3 /scripts/queryUser.py 2>&1 | tee /substra/data/log/queryUser.log"',
                                        'environment': ['GOPATH=/opt/gopath'],
                                        'volumes': ['/substra/data:/substra/data',
                                                    '/substra/conf:/substra/conf',
                                                    './python-scripts:/scripts'],
                                        'networks': ['substra'],
                                        'depends_on': ['run']},
                          'revoke': {'container_name': 'revoke',
                                     'image': 'substra/fabric-ca-tools',
                                     'command': '/bin/bash -c "python3 /scripts/revoke.py 2>&1 | tee /substra/data/log/revoke.log"',
                                     'environment': ['GOPATH=/opt/gopath'],
                                     'volumes': ['/substra/data:/substra/data',
                                                 '/substra/conf:/substra/conf',
                                                 './python-scripts:/scripts',
                                                 '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                     'networks': ['substra'],
                                     'depends_on': ['fixtures']},
                      },
                      'path': os.path.join(dir_path, '../docker-compose-dynamic.yaml')}

    for orderer in conf['orderers']:
        # RCA
        rca = {'container_name': orderer['ca']['host'],
               'image': 'substra/fabric-ca',
               'restart': 'unless-stopped',
               'working_dir': '/etc/hyperledger/',
               'ports': ['%s:%s' % (orderer['ca']['host_port'], orderer['ca']['port'])],
               'command': '/bin/bash -c "python3 start-root-ca.py 2>&1"',
               'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': ['/substra/data:/substra/data',
                           '/substra/backup/orgs/%s/rca:/etc/hyperledger/fabric-ca-server/' % orderer['name'],
                           '/substra/conf/%s/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml' %
                           orderer['name']],
               'networks': ['substra']}

        docker_compose['substra_tools']['setup']['depends_on'].append(orderer['ca']['host'])
        docker_compose['substra_tools']['setup']['volumes'].append(
            '/substra/conf/%s/fabric-ca-client-config.yaml:/root/cas/%s/fabric-ca-client-config.yaml' % (
                orderer['name'], orderer['ca']['host']))
        docker_compose['substra_services']['rca'].append((orderer['ca']['host'], rca))

        # ORDERER
        svc = {'container_name': orderer['host'],
               'image': 'substra/fabric-ca-orderer',
               'restart': 'unless-stopped',
               'working_dir': '/etc/hyperledger/',
               'command': 'python3 start-orderer.py 2>&1',
               'ports': ['%s:%s' % (orderer['port'], orderer['port'])],
               'environment': ['ORG=%s' % orderer['name'],
                               'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/fabric'],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': [
                   '/substra/data:/substra/data',
                   '%s:%s' % (conf_path, conf_path),
                   '/substra/backup/orgs/%s/%s:/var/hyperledger/production/orderer' % (orderer['name'], orderer['name']),
                   './python-scripts/util.py:/etc/hyperledger/util.py',
                   '/substra/conf/%s/fabric-ca-client-config.yaml:/etc/hyperledger/fabric/fabric-ca-client-config.yaml' %
                   orderer['name'],
                   '/substra/conf/%s/orderer.yaml:/etc/hyperledger/fabric/orderer.yaml' % orderer['name']],
               'networks': ['substra'],
               'depends_on': ['setup']}

        docker_compose['substra_tools']['run']['depends_on'].append(orderer['host'])
        docker_compose['substra_services']['svc'].append((orderer['host'], svc))

    for org in conf['orgs']:
        # RCA
        rca = {'container_name': org['ca']['host'],
               'image': 'substra/fabric-ca',
               'restart': 'unless-stopped',
               'working_dir': '/etc/hyperledger/',
               'ports': ['%s:%s' % (org['ca']['host_port'], org['ca']['port'])],
               'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
               'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': ['/substra/data:/substra/data',
                           '/substra/backup/orgs/%s/rca:/etc/hyperledger/fabric-ca-server/' % org['name'],
                           '/substra/conf/%s/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml' %
                           org['name']
                           ],
               'networks': ['substra']}

        docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
        docker_compose['substra_tools']['setup']['volumes'].append(
            '/substra/conf/%s/fabric-ca-client-config.yaml:/root/cas/%s/fabric-ca-client-config.yaml' % (
                org['name'], org['ca']['host']))
        docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

        # Peer

        for index, peer in enumerate(org['peers']):
            svc = {'container_name': peer['host'],
                   'image': 'substra/fabric-ca-peer',
                   'restart': 'unless-stopped',
                   'command': 'python3 start-peer.py 2>&1',
                   'environment': ['ORG=%s' % org['name'],
                                   'PEER_INDEX=%s' % index,
                                   'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/fabric/',
                                   ],
                   'working_dir': '/etc/hyperledger/',
                   'ports': ['%s:%s' % (peer['host_port'], peer['port']),
                             '%s:%s' % (peer['host_event_port'], peer['event_port'])],
                   'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
                   'volumes': ['/substra/data:/substra/data',
                               '%s:%s' % (conf_path, conf_path),
                               '/substra/backup/orgs/%s/%s/:/var/hyperledger/production/' % (org['name'], peer['name']),
                               './python-scripts/util.py:/etc/hyperledger/util.py',
                               '/var/run/docker.sock:/host/var/run/docker.sock',
                               '/substra/conf/%s/fabric-ca-client-config.yaml:/etc/hyperledger/fabric/fabric-ca-client-config.yaml' %
                               org['name'],
                               '/substra/conf/%s/%s/core.yaml:/etc/hyperledger/fabric/core.yaml' % (
                               org['name'], peer['name']),
                               ],
                   'networks': ['substra'],
                   'depends_on': ['setup']}

            docker_compose['substra_tools']['run']['depends_on'].append(peer['host'])
            docker_compose['substra_services']['svc'].append((peer['host'], svc))

    # Create all services along to conf

    COMPOSITION = {'services': {}, 'version': '2', 'networks': {'substra': None}}

    for name, dconfig in docker_compose['substra_services']['rca']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_services']['svc']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_tools'].items():
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_test'].items():
        COMPOSITION['services'][name] = dconfig

    with open(docker_compose['path'], 'w+') as f:
        f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose


def stop(docker_compose=None):
    print('stopping container', flush=True)
    call(['docker', 'rm', '-f', 'rca-orderer', 'rca-owkin', 'rca-chu-nantes', 'setup', 'orderer1-orderer',
          'peer1-owkin', 'peer2-owkin', 'peer1-chu-nantes', 'peer2-chu-nantes', 'run', 'fixtures', 'queryUser',
          'revoke'])
    call(['docker-compose', '-f', os.path.join(dir_path, '../docker-compose.yaml'), 'down', '--remove-orphans'])

    if docker_compose is not None:
        services = [name for name, _ in docker_compose['substra_services']['svc']]
        services += [name for name, _ in docker_compose['substra_services']['rca']]
        services += list(docker_compose['substra_tools'].keys())
        call(['docker', 'rm', '-f'] + services)
        call(['docker-compose', '-f', docker_compose['path'], 'down', '--remove-orphans'])
    else:
        call(['docker-compose', '-f', os.path.join(dir_path, '../docker-compose.yaml'), 'down', '--remove-orphans'])

    remove_chaincode_docker_containers()
    remove_chaincode_docker_images()


def start(conf, conf_path, fixtures):
    create_ca(conf)
    create_configtx(conf)
    create_core_peer_config(conf)
    create_orderer_config(conf)

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

    conf_path = '/substra/conf/conf.json'

    if args['no_backup']:
        # create directory with correct rights
        call(['rm', '-rf', '/substra/data'])
        call(['rm', '-rf', '/substra/conf'])

        create_directory('/substra/data/logs')
        create_directory('/substra/conf/')
        call(['rm', '-rf', '/substra/backup'])

    if not os.path.exists(conf_path):
        if args['config']:
            call(['python3', args['config']])
        else:
            call(['python3', os.path.join(dir_path, 'conf2orgs.py')])
    else:
        print('Use existing configuration in /substra/conf/conf.json', flush=True)

    conf = json.load(open(conf_path, 'r'))

    print('Build substra-network for : ', flush=True)
    print('  Orderer :')
    for orderer in conf['orderers']:
        print('   -', orderer['name'], flush=True)

    print('  Organizations :', flush=True)
    for org in conf['orgs']:
        print('   -', org['name'], flush=True)

    print('', flush=True)

    for org in conf['orgs'] + conf['orderers']:
        create_directory('/substra/data/orgs/%s' % org['name'])
        create_directory('/substra/conf/%s' % org['name'])

    start(conf, conf_path, args['fixtures'])

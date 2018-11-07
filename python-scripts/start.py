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


def create_ca_server_config(orgs):
    # For each org, create a config file from template
    for org_name in orgs.keys():
        org = orgs[org_name]

        stream = open(os.path.join(dir_path, '../templates/fabric-ca-server-config.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['tls']['certfile'] = org['tls']['certfile']

        yaml_data['ca']['name'] = org['ca']['name']
        yaml_data['ca']['certfile'] = org['ca']['certfile']

        yaml_data['csr']['cn'] = org['csr']['cn']
        yaml_data['csr']['hosts'] += org['csr']['hosts']

        yaml_data['registry']['identities'][0]['name'] = org['users']['bootstrap_admin']['name']
        yaml_data['registry']['identities'][0]['pass'] = org['users']['bootstrap_admin']['pass']

        filename = org['ca-server-config-path']
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_ca_client_config(orgs):
    # For each org, create a config file from template
    for org_name in orgs.keys():
        org = orgs[org_name]

        stream = open(os.path.join(dir_path, '../templates/fabric-ca-client-config.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        # https://hyperledger-fabric-ca.readthedocs.io/en/release-1.2/users-guide.html#enabling-tls
        yaml_data['tls']['certfiles'] = org['ca']['certfile']

        yaml_data['caname'] = org['ca']['name']

        yaml_data['csr']['cn'] = org['csr']['cn']
        yaml_data['csr']['hosts'] += org['csr']['hosts']

        yaml_data['url'] = org['ca']['url']

        # yaml_data['mspdir'] = org['users']['admin']['home'] + '/msp'  # for revoking user
        yaml_data['mspdir'] = org['msp_dir']  # for revoking user

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
        'host': conf['orderers'][x]['host'],
        'port': conf['orderers'][x]['port']
    } for x in conf['orderers'].keys()]

    orderers = [{
        'Name': x,
        'ID': conf['orderers'][x]['msp_id'],
        'MSPDir': conf['orderers'][x]['msp_dir'],
        # 'MSPDir': conf['orderers'][x]['users']['admin']['home'] + '/msp',
    } for x in conf['orderers'].keys()]

    orgs = [{
        'Name': x,
        'ID': conf['orgs'][x]['msp_id'],
        'MSPDir': conf['orgs'][x]['msp_dir'],
        # 'MSPDir': conf['orgs'][x]['users']['admin']['home'] + '/msp',
        'AnchorPeers': [{
            'Host': peer['host'],
            'Port': peer['port']
        } for peer in conf['orgs'][x]['peers'] if peer['anchor']]
    } for x in conf['orgs'].keys()]
    yaml_data['Organizations'] = orderers + orgs

    yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Organizations'] = orderers
    yaml_data['Profiles']['OrgsOrdererGenesis']['Consortiums']['SampleConsortium']['Organizations'] = orgs
    yaml_data['Profiles']['OrgsChannel']['Application']['Organizations'] = orgs

    filename = conf['misc']['configtx-config-path']
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_core_peer_config(conf):
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
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

            yaml_data['logging']['level'] = 'debug'

            create_directory(peer['docker_core_dir'])
            filename = '%(dir)s/core.yaml' % {'dir': peer['docker_core_dir']}
            with open(filename, 'w+') as f:
                f.write(dump(yaml_data, default_flow_style=False))

            ###############################
            # create if for host binaries #
            ###############################
            yaml_data['peer']['mspConfigPath'] = org['core']['host']['msp_config_path']
            yaml_data['peer']['address'] = '%(host)s:%(port)s' % {'host': peer['host'], 'port': peer['host_port']}

            create_directory(peer['host_core_dir'])
            filename = '%(dir)s/core.yaml' % {'dir': peer['host_core_dir']}
            with open(filename, 'w+') as f:
                f.write(dump(yaml_data, default_flow_style=False))


def create_orderer_config(conf):
    for org_name in conf['orderers'].keys():
        org = conf['orderers'][org_name]

        stream = open(os.path.join(dir_path, '../templates/orderer.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['General']['TLS']['Certificate'] = org['home'] + '/tls/' + org['tls']['cert']
        yaml_data['General']['TLS']['PrivateKey'] = org['home'] + '/tls/' + org['tls']['key']
        yaml_data['General']['TLS']['Enabled'] = 'true'
        yaml_data['General']['TLS']['ClientAuthRequired'] = 'true'
        yaml_data['General']['TLS']['RootCAs'] = [org['tls']['certfile']]
        yaml_data['General']['TLS']['ClientRootCAs'] = [org['tls']['certfile']]

        yaml_data['General']['ListenAddress'] = '0.0.0.0'
        yaml_data['General']['GenesisMethod'] = 'file'
        yaml_data['General']['GenesisFile'] = conf['misc']['genesis_bloc_file']
        yaml_data['General']['LocalMSPID'] = org['msp_id']
        yaml_data['General']['LocalMSPDir'] = org['local_msp_dir']
        yaml_data['General']['LogLevel'] = 'debug'

        yaml_data['Debug']['BroadcastTraceDir'] = org['broadcast_dir']

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
                                                'volumes': ['/substra/data:/substra/data',
                                                            '/substra/conf:/substra/conf', './python-scripts:/scripts',
                                                            '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                                'networks': ['substra'],
                                                'depends_on': []},
                                        },
                      'substra_test': {
                          'fixtures': {'container_name': 'fixtures',
                                       'image': 'substra/fabric-ca-tools',
                                       'command': '/bin/bash -c "python3 /scripts/%s 2>&1 | tee /substra/data/log/fixtures.log"' % conf['misc']['fixtures_path'],
                                       'environment': ['GOPATH=/opt/gopath'],
                                       'volumes': ['/substra/data:/substra/data',
                                                   '/substra/conf:/substra/conf',
                                                   './python-scripts:/scripts',
                                                   '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                       'networks': ['substra'],
                                       'depends_on': ['run']},
                          'test': {'container_name': 'test',
                                   'image': 'substra/fabric-ca-tools',
                                   'command': '/bin/bash -c "python3 /scripts/test.py 2>&1 | tee /substra/data/log/test.log"',
                                   'environment': ['GOPATH=/opt/gopath'],
                                   'volumes': ['/substra/data:/substra/data',
                                               '/substra/conf:/substra/conf',
                                               './python-scripts:/scripts'],
                                   'networks': ['substra'],
                                   'depends_on': ['run']},
                          'revoke': {'container_name': 'revoke',
                                     'image': 'substra/fabric-ca-tools',
                                     'command': '/bin/bash -c "python3 /scripts/revoke.py 2>&1 | tee /substra/data/log/test.log"',
                                     'environment': ['GOPATH=/opt/gopath'],
                                     'volumes': ['/substra/data:/substra/data',
                                                 '/substra/conf:/substra/conf',
                                                 './python-scripts:/scripts',
                                                 '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                     'networks': ['substra'],
                                     'depends_on': ['fixtures']},
                      },
                      'path': os.path.join(dir_path, '../docker-compose-dynamic.yaml')}

    for orderer_name, orderer_conf in conf['orderers'].items():
        # RCA
        rca = {'container_name': orderer_conf['ca']['host'],
               'image': 'substra/fabric-ca',
               'working_dir': '/etc/hyperledger/fabric-ca-server',
               'ports': ['%s:%s' % (orderer_conf['ca']['host_port'], orderer_conf['ca']['port'])],
               'command': '/bin/bash -c "python3 start-root-ca.py 2>&1 | tee /substra/data/logs/%s.log"' %
                          orderer_conf['ca']['host'],
               'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
               'volumes': ['/substra/data:/substra/data',
                           '/substra/conf/%s/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml' %
                           orderer_conf['name']],
               'networks': ['substra']}

        docker_compose['substra_tools']['setup']['depends_on'].append(orderer_conf['ca']['host'])
        docker_compose['substra_tools']['setup']['volumes'].append(
            '/substra/conf/%s/fabric-ca-client-config.yaml:/root/cas/%s/fabric-ca-client-config.yaml' % (
                orderer_conf['name'], orderer_conf['ca']['host']))
        docker_compose['substra_services']['rca'].append((orderer_conf['ca']['host'], rca))

        # ORDERER
        svc = {'container_name': orderer_conf['host'],
               'image': 'substra/fabric-ca-orderer',
               'working_dir': '/etc/hyperledger/orderer',
               'command': '/bin/bash -c "python3 start-orderer.py 2>&1 | tee /substra/data/logs/%s.log"' %
                          orderer_conf['host'],
               'environment': ['ORG=%s' % orderer_conf['name'],
                               'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/orderer'],
               'volumes': ['/substra/data:/substra/data',
                           '%s:%s' % (conf_path, conf_path),
                           './python-scripts/conf.py:/etc/hyperledger/orderer/conf.py',
                           './python-scripts/util.py:/etc/hyperledger/orderer/util.py',
                           '/substra/conf/%s/fabric-ca-client-config.yaml:/etc/hyperledger/orderer/fabric-ca-client-config.yaml' %
                           orderer_conf['name'],
                           '/substra/conf/%s/orderer.yaml:/etc/hyperledger/fabric/orderer.yaml' % orderer_conf['name']],
               'networks': ['substra'],
               'depends_on': ['setup']}

        docker_compose['substra_tools']['run']['depends_on'].append(orderer_conf['host'])
        docker_compose['substra_services']['svc'].append((orderer_conf['host'], svc))

    for org_name, org_conf in conf['orgs'].items():
        # RCA
        rca = {'container_name': org_conf['ca']['host'],
               'image': 'substra/fabric-ca',
               'working_dir': '/etc/hyperledger/fabric-ca-server',
               'ports': ['%s:%s' % (org_conf['ca']['host_port'], org_conf['ca']['port'])],
               'command': '/bin/bash -c "python3 start-root-ca.py 2>&1 | tee /substra/data/logs/%s.log"' %
                          org_conf['ca']['host'],
               'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
               'volumes': ['/substra/data:/substra/data',
                           '/substra/conf/%s/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml' %
                           org_conf['name']],
               'networks': ['substra']}

        docker_compose['substra_tools']['setup']['depends_on'].append(org_conf['ca']['host'])
        docker_compose['substra_tools']['setup']['volumes'].append(
            '/substra/conf/%s/fabric-ca-client-config.yaml:/root/cas/%s/fabric-ca-client-config.yaml' % (
                org_conf['name'], org_conf['ca']['host']))
        docker_compose['substra_services']['rca'].append((org_conf['ca']['host'], rca))

        # Peer

        for index, peer in enumerate(org_conf['peers']):
            svc = {'container_name': peer['host'],
                   'image': 'substra/fabric-ca-peer',
                   'command': '/bin/bash -c "python3 start-peer.py 2>&1 | tee /substra/data/logs/%s.log"' %
                              peer['host'],
                   'environment': ['ORG=%s' % org_conf['name'],
                                   'PEER_INDEX=%s' % index,
                                   'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/fabric/'],
                   'working_dir': '/etc/hyperledger/fabric/',
                   'ports': ['%s:%s' % (peer['host_port'], peer['port']),
                             '%s:%s' % (peer['host_event_port'], peer['event_port'])],
                   'volumes': ['/substra/data:/substra/data',
                               '%s:%s' % (conf_path, conf_path),
                               './python-scripts/conf.py:/etc/hyperledger/fabric/conf.py',
                               './python-scripts/util.py:/etc/hyperledger/fabric/util.py',
                               '/var/run:/host/var/run',
                               '/substra/conf/%s/fabric-ca-client-config.yaml:/etc/hyperledger/fabric/fabric-ca-client-config.yaml' %
                               org_conf['name'],
                               '/substra/conf/%s/%s/core.yaml:/etc/hyperledger/fabric/core.yaml' % (
                                   org_conf['name'], peer['name'])],
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
          'peer1-owkin', 'peer2-owkin', 'peer1-chu-nantes', 'peer2-chu-nantes', 'run', 'fixtures', 'test', 'revoke'])
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
    services = [name for name, _ in docker_compose['substra_services']['rca']] + ['setup']
    call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--remove-orphans'] + services)
    call(['docker', 'ps', '-a'])

    # Wait for the setup container to complete
    dowait('the \'setup\' container to finish registering identities, creating the genesis block and other artifacts',
           90, conf['misc']['setup_logfile'],
           [conf['misc']['setup_success_file']])

    services = [name for name, _ in docker_compose['substra_services']['svc']]
    call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps'] + services)

    peers_orgs_files = []
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        peers_orgs_files = [peer['tls']['clientCert'] for peer in org['peers']]

    dowait('the docker \'peer\' containers to complete',
           30, None,
           peers_orgs_files)

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

        # Load Tests
        call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'test'])

        #####################################
        # uncomment for revoking user owkin #
        #####################################
        # Revoke User
        call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'revoke'])


if __name__ == "__main__":
    # create directory with correct rights
    call(['rm', '-rf', '/substra/data'])
    call(['rm', '-rf', '/substra/conf'])

    create_directory('/substra/data/logs')
    create_directory('/substra/conf/')

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', nargs='?', type=str, action='store', default='',
                        help="JSON config file to be used")
    parser.add_argument('-f', '--fixtures', action='store_true', default=False,
                        help="Load fixtures")
    args = vars(parser.parse_args())

    conf_path = '/substra/conf/conf.json'

    if args['config']:
        call(['python3', args['config']])
    else:
        call(['python3', os.path.join(dir_path, 'conf2orgs.py')])

    conf = json.load(open(conf_path, 'r'))

    print('Build substra-network for : ', flush=True)
    print('  Orderer :')
    for org_name in conf['orderers'].keys():
        print('   -', org_name, flush=True)

    print('  Organizations :', flush=True)
    for org_name in conf['orgs'].keys():
        print('   -', org_name, flush=True)

    print('', flush=True)

    for org in list(conf['orgs'].keys()) + list(conf['orderers'].keys()):
        create_directory('/substra/data/orgs/%s' % org)
        create_directory('/substra/conf/%s' % org)

    start(conf, conf_path, args['fixtures'])

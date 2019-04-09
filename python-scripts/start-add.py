import os
import json

from subprocess import call
from util import dowait, create_directory, remove_chaincode_docker_images, remove_chaincode_docker_containers
from start import create_ca_server_config, create_ca_client_config, create_core_peer_config, create_fabric_ca_peer_config, create_substrabac_config
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

dir_path = os.path.dirname(os.path.realpath(__file__))

LOGGING_LEVEL = ['critical', 'error', 'warning', 'notice', 'info', 'debug']
SUBSTRA_PATH = '/substra'


def create_ca(conf):
    print('Creating ca server/client files for each org', flush=True)
    create_ca_server_config(conf['orgs'])
    create_ca_client_config(conf['orgs'])


def create_configtx(conf):
    print('Creating configtx of the substra network', flush=True)
    yaml_data = {}

    orgs = [{
        'Name': x['name'],
        'ID': x['msp_id'],
        'MSPDir': f"{x['users']['admin']['home']}/msp",
        'AnchorPeers': [{
            'Host': peer['host'],
            'Port': peer['port']
        } for peer in x['peers'] if peer['anchor']]
    } for x in conf['orgs']]
    yaml_data['Organizations'] = orgs

    profiles = {'OrgsChannel': {'Application': {'Organizations': orgs}}}
    yaml_data['Profiles'] = profiles

    filename = conf['misc']['configtx-config-path']
    filename_global = filename.replace('configtx', 'configtx-global')

    # Rename configtx
    os.rename(filename, filename_global)

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
                      'substra_tools': {'setup-add': {'container_name': 'setup-add',
                                                      'image': 'substra/substra-ca-tools',
                                                      'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup-add.py 2>&1| tee {SUBSTRA_PATH}/data/log/setup.log"',
                                                      'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server',
                                                                      f'FABRIC_CFG_PATH={SUBSTRA_PATH}/data'],
                                                      'volumes': [f'{SUBSTRA_PATH}/data:{SUBSTRA_PATH}/data',
                                                                  f'{SUBSTRA_PATH}/conf:{SUBSTRA_PATH}/conf',
                                                                  './python-scripts:/scripts',
                                                                  f'{conf_path}:{conf_path}'],
                                                      'networks': ['net_substra'],
                                                      'depends_on': []},

                                        'run-add': {'container_name': 'run-add',
                                                    'image': 'substra/substra-ca-tools',
                                                    'command': f'/bin/bash -c "set -o pipefail;sleep 3;python3 /scripts/run_add.py 2>&1 ; sleep 9999 | tee {SUBSTRA_PATH}/data/log/run.log"',
                                                    'environment': ['GOPATH=/opt/gopath',
                                                                    f'FABRIC_CFG_PATH={SUBSTRA_PATH}/data'],
                                                    'volumes': ['/var/run/docker.sock:/var/run/docker.sock',
                                                                f'{SUBSTRA_PATH}/data:{SUBSTRA_PATH}/data',
                                                                f'{SUBSTRA_PATH}/conf:{SUBSTRA_PATH}/conf',
                                                                './python-scripts:/scripts',
                                                                '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'
                                                                ],
                                                    'networks': ['net_substra'],
                                                    'depends_on': []},
                                        },
                      'path': os.path.join(dir_path, '../docker-compose-dynamic-add.yaml')}

    for org in conf['orgs']:
        # RCA
        rca = {'container_name': org['ca']['host'],
               'image': 'substra/substra-ca',
               'restart': 'unless-stopped',
               'working_dir': '/etc/hyperledger/',
               'ports': [f"{org['ca']['host_port']}:{org['ca']['port']}"],
               'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
               'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': [f'{SUBSTRA_PATH}/data:{SUBSTRA_PATH}/data',
                           f"{SUBSTRA_PATH}/backup/orgs/{org['name']}/rca:/etc/hyperledger/fabric-ca-server/",
                           f"{SUBSTRA_PATH}/conf/{org['name']}/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml"
                           ],
               'networks': ['net_substra']}

        docker_compose['substra_tools']['setup-add']['depends_on'].append(org['ca']['host'])
        docker_compose['substra_tools']['setup-add']['volumes'].append(
            f"{SUBSTRA_PATH}/conf/{org['name']}/fabric-ca-client-config.yaml:/root/cas/{org['ca']['host']}/fabric-ca-client-config.yaml")
        docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

        # Peer
        for index, peer in enumerate(org['peers']):
            svc = {'container_name': peer['host'],
                   'image': 'substra/substra-ca-peer',
                   'restart': 'unless-stopped',
                   'command': 'python3 start-peer.py 2>&1',
                   'environment': [# https://medium.com/@Alibaba_Cloud/hyperledger-fabric-deployment-on-alibaba-cloud-environment-sigsegv-problem-analysis-and-solutions-9a708313f1a4
                                   'GODEBUG=netdns=go+1',
                                   'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/fabric/',
                                   ],
                   'working_dir': '/etc/hyperledger/',
                   'ports': [f"{peer['host_port']}:{peer['port']}",
                             f"{peer['host_event_port']}:{peer['event_port']}"],
                   'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
                   'volumes': [f'{SUBSTRA_PATH}/data:{SUBSTRA_PATH}/data',
                               f"{SUBSTRA_PATH}/conf/{org['name']}/{peer['name']}/conf.json:/substra/conf/conf.json",
                               f"{SUBSTRA_PATH}/backup/orgs/{org['name']}/{peer['name']}/:/var/hyperledger/production/",
                               './python-scripts/util.py:/etc/hyperledger/util.py',
                               '/var/run/docker.sock:/host/var/run/docker.sock',
                               f"{SUBSTRA_PATH}/conf/{org['name']}/fabric-ca-client-config.yaml:/etc/hyperledger/fabric/fabric-ca-client-config.yaml",
                               f"{SUBSTRA_PATH}/conf/{org['name']}/{peer['name']}/core.yaml:/etc/hyperledger/fabric/core.yaml",
                               ],
                   'networks': ['net_substra'],
                   'depends_on': ['setup-add']}

            docker_compose['substra_tools']['run-add']['depends_on'].append(peer['host'])
            docker_compose['substra_services']['svc'].append((peer['host'], svc))

    # Create all services along to conf

    COMPOSITION = {'services': {}, 'version': '2', 'networks': {'net_substra': {'external': True}}}

    for name, dconfig in docker_compose['substra_services']['rca']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_services']['svc']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_tools'].items():
        COMPOSITION['services'][name] = dconfig

    with open(docker_compose['path'], 'w+') as f:
        f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose


def stop(docker_compose=None):
    print('stopping container', flush=True)
    call(['docker', 'rm', '-f', 'rca-chu-nantes', 'setup-add', 'peer1-chu-nantes', 'peer2-chu-nantes', 'run-add'])

    services = [name for name, _ in docker_compose['substra_services']['svc']]
    services += [name for name, _ in docker_compose['substra_services']['rca']]
    services += list(docker_compose['substra_tools'].keys())
    call(['docker', 'rm', '-f'] + services)
    call(['docker-compose', '-f', docker_compose['path'], 'down'])
    # remove_chaincode_docker_containers()
    # remove_chaincode_docker_images()


def start(conf, conf_path):
    create_ca(conf)
    create_configtx(conf)

    create_core_peer_config(conf)
    create_fabric_ca_peer_config(conf)

    create_substrabac_config(conf)

    print('Generate docker-compose file\n')
    docker_compose = generate_docker_compose_file(conf, conf_path)

    stop(docker_compose)

    print('start docker-compose', flush=True)
    services = [name for name, _ in docker_compose['substra_services']['rca']]

    if not os.path.exists(conf['misc']['setup_success_file']):
        services += ['setup-add']
    else:
        os.remove(conf['misc']['setup_success_file'])
        services += ['setup-add']

    call(['docker-compose', '-f', docker_compose['path'], 'up', '-d'] + services)
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

    if os.path.exists(conf['misc']['run_success_file']):
        os.remove(conf['misc']['run_success_file'])

    call(['docker-compose', '-f', docker_compose['path'], 'up', '-d', '--no-deps', 'run-add'])

    # Wait for the run container to start and complete
    dowait('the docker \'run\' container to run and complete',
           160, conf['misc']['run_logfile'],
           [conf['misc']['run_success_file']])


if __name__ == '__main__':

    conf_path = f'{SUBSTRA_PATH}/conf/conf-add.json'

    if not os.path.exists(conf_path):
        call(['python3', os.path.join(dir_path, 'conf/addorg.py')])
    else:
        print(f'Use existing configuration in {SUBSTRA_PATH}/conf/conf-add.json', flush=True)

    conf = json.load(open(conf_path, 'r'))

    print('Complete substra-network for : ', flush=True)
    print('  Organizations :', flush=True)
    for org in conf['orgs']:
        print('   -', org['name'], flush=True)

    print('', flush=True)

    for org in conf['orgs']:
        create_directory(f"{SUBSTRA_PATH}/dryrun/{org['name']}")

    for org in conf['orgs']:
        create_directory(f"{SUBSTRA_PATH}/data/orgs/{org['name']}")
        create_directory(f"{SUBSTRA_PATH}/conf/{org['name']}")

    orderer = conf['orderers'][0]
    start(conf, conf_path)

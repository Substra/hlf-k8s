import os
import yaml

HLF_VERSION = '1.4.1'


def generate_docker_compose_org(org, substra_path, network):

    FABRIC_CA_HOME = '/etc/hyperledger/fabric-ca-server'
    FABRIC_CFG_PATH = f'{substra_path}/data'
    FABRIC_CA_CLIENT_HOME = '/etc/hyperledger/fabric'

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': f'setup-{org["name"]}',
                                                  'image': 'substra/substra-ca-tools',
                                                  'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup.py 2>&1 | tee {substra_path}/data/log/setup-{org["name"]}.log"',
                                                  'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}',
                                                                  f'FABRIC_CFG_PATH={FABRIC_CFG_PATH}',
                                                                  f'FABRIC_CA_CLIENT_HOME={FABRIC_CA_CLIENT_HOME}'],
                                                  'volumes': ['./python-scripts:/scripts',
                                                              f'{substra_path}/data/log:{substra_path}/data/log',
                                                              f'{substra_path}/conf/config/conf-{org["name"]}.json:/{substra_path}/conf.json',
                                                              f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',
                                                              f'{substra_path}/conf/{org["name"]}/fabric-ca-client-config.yaml:{FABRIC_CA_CLIENT_HOME}/fabric-ca-client-config.yaml'],
                                                  'networks': [network],
                                                  'depends_on': [],
                                                  },

                                        'run': {'container_name': f'run-{org["name"]}',
                                                'image': 'substra/substra-ca-tools',
                                                'command': f'/bin/bash -c "set -o pipefail;sleep 3;python3 /scripts/run.py 2>&1 | tee {substra_path}/data/log/run-{org["name"]}.log"',
                                                'environment': ['GOPATH=/opt/gopath',
                                                                f'FABRIC_CFG_PATH={FABRIC_CFG_PATH}'],
                                                'volumes': ['/var/run/docker.sock:/var/run/docker.sock',
                                                            './python-scripts:/scripts',
                                                            f'{substra_path}/data/log/:{substra_path}/data/log/',
                                                            f'{substra_path}/data/channel/:{substra_path}/data/channel/',
                                                            f'{substra_path}/data/orgs/:{substra_path}/data/orgs/',
                                                            f'{substra_path}/conf/:{substra_path}/conf/',
                                                            f'{substra_path}/conf/config/conf-{org["name"]}.json:/{substra_path}/conf.json',
                                                            f'{substra_path}/data/configtx-{org["name"]}.yaml:{FABRIC_CFG_PATH}/configtx.yaml',
                                                            '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'
                                                            ],
                                                'networks': [network],
                                                'depends_on': [],
                                                }
                                        },
                      'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{org["name"]}.yaml')}

    # RCA
    rca = {'container_name': org['ca']['host'],
           'image': f'hyperledger/fabric-ca:{HLF_VERSION}',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'ports': [f'{org["ca"]["host_port"]}:{org["ca"]["port"]}'],
           'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
           'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}'],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',
                       f'{substra_path}/backup/orgs/{org["name"]}/rca:{FABRIC_CA_HOME}',
                       f'{substra_path}/conf/{org["name"]}/fabric-ca-server-config.yaml:{FABRIC_CA_HOME}/fabric-ca-server-config.yaml'
                       ],
           'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
    docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

    # Peer
    for index, peer in enumerate(org['peers']):
        svc = {'container_name': peer['host'],
               'image': f'hyperledger/fabric-peer:{HLF_VERSION}',
               'restart': 'unless-stopped',
               'command': '/bin/bash -c "peer node start 2>&1"',
               'environment': [# https://medium.com/@Alibaba_Cloud/hyperledger-fabric-deployment-on-alibaba-cloud-environment-sigsegv-problem-analysis-and-solutions-9a708313f1a4
                               'GODEBUG=netdns=go+1'],
               'working_dir': '/etc/hyperledger/',
               'ports': [f'{peer["host_port"]}:{peer["port"]}',
                         f'{peer["host_event_port"]}:{peer["event_port"]}'],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': ['/var/run/docker.sock:/host/var/run/docker.sock',
                           f'{substra_path}/data/channel/:{substra_path}/data/channel/',
                           f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',
                           f'{substra_path}/backup/orgs/{org["name"]}/{peer["name"]}/:/var/hyperledger/production/',
                           f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/fabric/msp/:{org["core"]["docker"]["msp_config_path"]}',
                           f'{substra_path}/conf/{org["name"]}/{peer["name"]}/core.yaml:{FABRIC_CA_CLIENT_HOME}/core.yaml',
                           ],
               'networks': [network],
               'depends_on': ['setup']}

        docker_compose['substra_tools']['run']['depends_on'].append(peer['host'])
        docker_compose['substra_tools']['setup']['volumes'].append(f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/fabric/msp/:{org["core"]["docker"]["msp_config_path"]}/{peer["name"]}',)
        docker_compose['substra_services']['svc'].append((peer['host'], svc))

        # Create all services along to conf

        COMPOSITION = {'services': {}, 'version': '2', 'networks': {network: {'external': True}}}

        for name, dconfig in docker_compose['substra_services']['rca']:
            COMPOSITION['services'][name] = dconfig

        for name, dconfig in docker_compose['substra_services']['svc']:
            COMPOSITION['services'][name] = dconfig

        for name, dconfig in docker_compose['substra_tools'].items():
            COMPOSITION['services'][name] = dconfig

        with open(docker_compose['path'], 'w+') as f:
            f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose


def generate_docker_compose_orderer(orderer, substra_path, network, genesis_bloc_file):

    FABRIC_CA_HOME = '/etc/hyperledger/fabric-ca-server'
    FABRIC_CFG_PATH = f'{substra_path}/data'
    FABRIC_CA_CLIENT_HOME = '/etc/hyperledger/fabric'

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': 'setup',
                                                  'image': 'substra/substra-ca-tools',
                                                  'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup.py 2>&1 | tee {substra_path}/data/log/setup-{orderer["name"]}.log"',
                                                  'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}',
                                                                  f'FABRIC_CFG_PATH={FABRIC_CFG_PATH}',
                                                                  f'FABRIC_CA_CLIENT_HOME={FABRIC_CA_CLIENT_HOME}'],
                                                  'volumes': ['./python-scripts:/scripts',
                                                              f'{substra_path}/data/log:{substra_path}/data/log',
                                                              f'{substra_path}/data/genesis:{substra_path}/data/genesis',
                                                              f'{substra_path}/conf/config/conf-{orderer["name"]}.json:{substra_path}/conf.json',
                                                              f'{substra_path}/data/configtx-{orderer["name"]}.yaml:{FABRIC_CFG_PATH}/configtx.yaml',
                                                              f'{substra_path}/data/orgs/{orderer["name"]}/fabric/msp/:{orderer["local_msp_dir"]}',
                                                              f'{substra_path}/data/orgs/{orderer["name"]}:{substra_path}/data/orgs/{orderer["name"]}',
                                                              f'{substra_path}/conf/{orderer["name"]}/fabric-ca-client-config.yaml:{FABRIC_CA_CLIENT_HOME}/fabric-ca-client-config.yaml',
                                                              ],
                                                  'networks': [network],
                                                  'depends_on': []}},
                      'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{orderer["name"]}.yaml')}

    # RCA
    rca = {'container_name': orderer['ca']['host'],
           'image': f'hyperledger/fabric-ca:{HLF_VERSION}',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'ports': [f"{orderer['ca']['host_port']}:{orderer['ca']['port']}"],
           'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
           'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}'],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [f'{substra_path}/data/orgs/{orderer["name"]}:{substra_path}/data/orgs/{orderer["name"]}',
                       f"{substra_path}/backup/orgs/{orderer['name']}/rca:{FABRIC_CA_HOME}",
                       f"{substra_path}/conf/{orderer['name']}/fabric-ca-server-config.yaml:{FABRIC_CA_HOME}/fabric-ca-server-config.yaml"],
           'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(orderer['ca']['host'])
    docker_compose['substra_services']['rca'].append((orderer['ca']['host'], rca))

    # ORDERER
    svc = {'container_name': orderer['host'],
           'image': f'hyperledger/fabric-orderer:{HLF_VERSION}',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'command': '/bin/bash -c "orderer 2>&1"',
           'ports': [f"{orderer['port']}:{orderer['port']}"],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [
               f'{genesis_bloc_file}:{genesis_bloc_file}',
               f'{substra_path}/data/orgs/{orderer["name"]}:{substra_path}/data/orgs/{orderer["name"]}',
               f"{substra_path}/backup/orgs/{orderer['name']}/{orderer['name']}:/var/hyperledger/production/orderer",
               f"{substra_path}/data/orgs/{orderer['name']}/fabric/msp/:{orderer['local_msp_dir']}",
               f"{substra_path}/conf/{orderer['name']}/core.yaml:{FABRIC_CA_CLIENT_HOME}/core.yaml",
               f"{substra_path}/conf/{orderer['name']}/orderer.yaml:{FABRIC_CA_CLIENT_HOME}/orderer.yaml"],
           'networks': [network],
           'depends_on': ['setup']}

    docker_compose['substra_services']['svc'].append((orderer['host'], svc))

    # Create all services along to conf

    COMPOSITION = {'services': {}, 'version': '2', 'networks': {network: {'external': True}}}

    for name, dconfig in docker_compose['substra_services']['rca']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_services']['svc']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_tools'].items():
        COMPOSITION['services'][name] = dconfig

    with open(docker_compose['path'], 'w+') as f:
        f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose

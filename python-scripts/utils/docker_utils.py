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
import yaml

HLF_VERSION = '1.4.6'

fabric_base_directory = '/etc/hyperledger/fabric'

SUBSTRA_CHAINCODE_PATH = os.getenv('SUBSTRA_CHAINCODE_PATH', '../substra-chaincode/chaincode')


def generate_docker_compose_org(org, conf_orderer, substra_path, network):

    orderer = conf_orderer['orderers'][0]

    FABRIC_CA_HOME = '/etc/hyperledger/fabric-ca-server'

    # Docker compose config
    docker_compose = {
        'substra_services': {
            'rca': [],
            'svc': []},
        'substra_tools': {
            'setup': {
                'container_name': f'setup-{org["name"]}',
                'labels': ['substra'],
                'image': 'substra/substra-ca-tools',
                'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup.py 2>&1 | tee {substra_path}/data/log/setup-{org["name"]}.log"',
                'environment': [f'SUBSTRA_PATH={substra_path}'],
                'volumes': [f'{substra_path}/data/log:{substra_path}/data/log',
                            f'{substra_path}/conf/config/conf-{org["name"]}.json:{substra_path}/conf.json',

                            # Admin MSP
                            f'{org["users"]["admin"]["home"]}:{org["users"]["admin"]["home"]}',
                            # User MSP
                            f'{org["users"]["user"]["home"]}:{org["users"]["user"]["home"]}',

                            # CA
                            f'{org["ca"]["certfile"]["external"]}:{org["ca"]["certfile"]["internal"]}'],
                'networks': [network],
                'depends_on': [],
            },

            'run': {
                'container_name': f'run-{org["name"]}',
                'labels': ['substra'],
                'image': 'substra/substra-ca-tools',
                'command': f'/bin/bash -c "set -o pipefail;sleep 3;python3 /scripts/run.py 2>&1 | tee {substra_path}/data/log/run-{org["name"]}.log"',
                'environment': ['GOPATH=/opt/gopath',
                                f'SUBSTRA_PATH={substra_path}',
                                f'ORG={org["name"]}',
                                'ENV=internal'],
                'volumes': [
                    # docker in docker
                    '/var/run/docker.sock:/var/run/docker.sock',

                    # logs
                    f'{substra_path}/data/log/:{substra_path}/data/log/',

                    # chaincode
                    f'{SUBSTRA_CHAINCODE_PATH}:/opt/gopath/src/chaincode',

                    # channel
                    f'{substra_path}/data/channel/:{substra_path}/data/channel/',

                    # run need to access all informations in multiple orgs
                    f'{substra_path}/data/orgs/:{substra_path}/data/orgs/',

                    # conf files
                    f'{substra_path}/conf/:{substra_path}/conf/',

                    # tls external
                    f"{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}:{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}",
                ],
                'networks': [network],
                'depends_on': [],
                }
                          },
        'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{org["name"]}.yaml')}

    # Extra dir for setup and run
    for index, peer in enumerate(org['peers']):
        # User MSP
        docker_compose['substra_tools']['setup']['volumes'].append(
            f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/msp/:{org["core_dir"]["internal"]}/{peer["name"]}/msp'  # noqa
        )
        docker_compose['substra_tools']['run']['volumes'].append(
            f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/msp/:{org["core_dir"]["internal"]}/{peer["name"]}/msp'  # noqa
        )
        # Client/Server TLS
        docker_compose['substra_tools']['setup']['volumes'].append(
            f'{peer["tls"]["dir"]["external"]}:{peer["tls"]["dir"]["external"]}')
        docker_compose['substra_tools']['run']['volumes'].append(
            f'{peer["tls"]["dir"]["external"]}:{peer["tls"]["dir"]["external"]}')

    # RCA
    rca = {
        'container_name': org['ca']['host'],
        'labels': ['substra'],
        'image': f'hyperledger/fabric-ca:{HLF_VERSION}',
        'restart': 'unless-stopped',
        'working_dir': '/etc/hyperledger/',
        'ports': [
            f'{org["ca"]["port"]["external"]}:{org["ca"]["port"]["internal"]}'
        ],
        'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
        'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}'],
        'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
        'volumes': [
            f'{substra_path}/data/orgs/{org["name"]}:{fabric_base_directory}/ca/',
            f'{substra_path}/backup/orgs/{org["name"]}/rca:{FABRIC_CA_HOME}',
            f'{substra_path}/conf/{org["name"]}/fabric-ca-server-config.yaml:{FABRIC_CA_HOME}/fabric-ca-server-config.yaml'  # noqa
        ],
        'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
    docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

    # Peer
    for _, peer in enumerate(org['peers']):
        svc = {
            'container_name': peer['host'],
            'labels': ['substra'],
            'image': f'hyperledger/fabric-peer:{HLF_VERSION}',
            'restart': 'unless-stopped',
            'command': '/bin/bash -c "peer node start 2>&1"',
            'environment': [
                # https://medium.com/@Alibaba_Cloud/hyperledger-fabric-deployment-on-alibaba-cloud-environment-sigsegv-problem-analysis-and-solutions-9a708313f1a4
                'GODEBUG=netdns=go+1'
            ],
            'working_dir': fabric_base_directory,
            'ports': [
                f'{peer["port"]["external"]}:{peer["port"]["internal"]}',
                f'{peer["operations"]["prometheus"]["port"]["external"]}:{peer["operations"]["prometheus"]["port"]["internal"]}',
                f'{peer["operations"]["statsd"]["port"]["external"]}:{peer["operations"]["statsd"]["port"]["internal"]}',
            ],
            'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
            'volumes': [
                # docker in docker chaincode
                '/var/run/docker.sock:/host/var/run/docker.sock',

                # backup files
                f'{substra_path}/backup/orgs/{org["name"]}/{peer["name"]}/:/var/hyperledger/production/',

                # tls peer server files
                f"{peer['tls']['dir']['external']}/{peer['tls']['server']['dir']}:{peer['tls']['dir']['internal']}/{peer['tls']['server']['dir']}",  # noqa
                # tls peer client files
                f"{peer['tls']['dir']['external']}/{peer['tls']['client']['dir']}:{peer['tls']['dir']['internal']}/{peer['tls']['client']['dir']}",  # noqa
                # tls orderer client files
                f"{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}:{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}",  # noqa

                # msp
                f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/msp/:{org["core_dir"]["internal"]}/msp',

                # conf files
                f'{substra_path}/conf/{org["name"]}/{peer["name"]}/core.yaml:{org["core_dir"]["internal"]}/core.yaml',

                # ca file
                f"{org['ca']['certfile']['external']}:{org['ca']['certfile']['internal']}",
            ],
            'networks': [network],
            'depends_on': ['setup']
        }

        # run
        docker_compose['substra_tools']['run']['depends_on'].append(peer['host'])

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


def generate_docker_compose_orderer(org, substra_path, network):

    genesis_bloc_file = org['misc']['genesis_bloc_file']

    FABRIC_CA_HOME = '/etc/hyperledger/fabric-ca-server'

    # Docker compose config
    docker_compose = {
        'substra_services': {
            'rca': [],
            'svc': []},
        'substra_tools': {
            'setup': {
                'container_name': f'setup-{org["name"]}',
                'labels': ['substra'],
                'image': 'substra/substra-ca-tools',
                'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup.py 2>&1 | tee {substra_path}/data/log/setup-{ org["name"]}.log"',
                'environment': [f'SUBSTRA_PATH={substra_path}'],
                'volumes': [f'{substra_path}/data/log:{substra_path}/data/log',
                            f'{substra_path}/data/genesis:{substra_path}/data/genesis',
                            f'{substra_path}/conf/config/conf-{org["name"]}.json:{substra_path}/conf.json',
                            # access to config tx file
                            f'{substra_path}/data/orgs/{org["name"]}/:{substra_path}/data/orgs/{org["name"]}',

                            # Admin MSP
                            f'{org["users"]["admin"]["home"]}:{org["users"]["admin"]["home"]}',
                            # CA
                            f'{org["ca"]["certfile"]["external"]}:{org["ca"]["certfile"]["internal"]}',

                            # broadcast dir
                            f'{org["broadcast_dir"]["external"]}:{org["broadcast_dir"]["internal"]}',

                            ],
                'networks': [network],
                'depends_on': []}},
        'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{org["name"]}.yaml')}
    # Extra dir for setup
    for index, orderer in enumerate(org['orderers']):
        # User MSP
        docker_compose['substra_tools']['setup']['volumes'].append(
            f'{substra_path}/data/orgs/{org["name"]}/{orderer["name"]}/:{org["core_dir"]["internal"]}/{orderer["name"]}/'  # noqa
        )
        # Client/Server TLS
        docker_compose['substra_tools']['setup']['volumes'].append(
            f'{orderer["tls"]["dir"]["external"]}/:{orderer["tls"]["dir"]["external"]}'
        )

    # RCA
    rca = {
        'container_name': org['ca']['host'],
        'labels': ['substra'],
        'image': f'hyperledger/fabric-ca:{HLF_VERSION}',
        'restart': 'unless-stopped',
        'working_dir': '/etc/hyperledger/',
        'ports': [f"{org['ca']['port']['external']}:{org['ca']['port']['internal']}"],
        'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
        'environment': [
            f'FABRIC_CA_HOME={FABRIC_CA_HOME}'
        ],
        'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
        'volumes': [
            f'{substra_path}/data/orgs/{org["name"]}:{fabric_base_directory}/ca/',
            f"{substra_path}/backup/orgs/{org['name']}/rca:{FABRIC_CA_HOME}",
            f"{substra_path}/conf/{org['name']}/fabric-ca-server-config.yaml:{FABRIC_CA_HOME}/fabric-ca-server-config.yaml"  # noqa
        ],
        'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
    docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

    # ORDERER
    for _, orderer in enumerate(org['orderers']):
        svc = {
            'container_name': orderer['host'],
            'labels': ['substra'],
            'image': f'hyperledger/fabric-orderer:{HLF_VERSION}',
            'restart': 'unless-stopped',
            'working_dir': fabric_base_directory,
            'command': '/bin/bash -c "orderer 2>&1"',
            'ports': [
                f"{orderer['port']['external']}:{orderer['port']['internal']}",
                f'{orderer["operations"]["prometheus"]["port"]["external"]}:{orderer["operations"]["prometheus"]["port"]["internal"]}',
                f'{orderer["operations"]["statsd"]["port"]["external"]}:{orderer["operations"]["statsd"]["port"]["internal"]}',
            ],
            'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
            'volumes': [
                # genesis file
                f'{genesis_bloc_file["external"]}:{genesis_bloc_file["internal"]}',

                # broadcast dir
                f'{org["broadcast_dir"]["external"]}:{org["broadcast_dir"]["internal"]}',

                # backup files
                f"{substra_path}/backup/orgs/{org['name']}/{orderer['name']}:/var/hyperledger/production/orderer",

                # msp
                f'{substra_path}/data/orgs/{org["name"]}/{orderer["name"]}/msp/:{org["core_dir"]["internal"]}/msp',

                # tls server files
                f"{orderer['tls']['dir']['external']}/{orderer['tls']['server']['dir']}:{orderer['tls']['dir']['internal']}/{orderer['tls']['server']['dir']}",

                # conf files
                f"{substra_path}/conf/{org['name']}/{orderer['name']}/core.yaml:{org['core_dir']['internal']}/core.yaml",
                f"{substra_path}/conf/{org['name']}/{orderer['name']}/orderer.yaml:{org['core_dir']['internal']}/orderer.yaml",

                # ca file
                f"{org['ca']['certfile']['external']}:{org['ca']['certfile']['internal']}",
            ],
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


def generate_docker(substra_path, specs, network):
    path = os.path.join(substra_path, 'dockerfiles', f'docker-compose-{specs["name"]}.yaml')

    COMPOSITION = {
        'services':
            {specs['name']:
                {'container_name': specs['name'],
                 'labels': ['substra'],
                 'image': 'substra/substra-ca-tools',
                 'command': f'/bin/bash -c "set -o pipefail;python3 {specs["filepath"]} 2>&1 | '
                            f'tee {substra_path}/data/log/{specs["name"]}.log"',
                 'environment': ['ENV=internal', f'SUBSTRA_PATH={substra_path}'],
                 'volumes': [
                    f'{substra_path}/data/:{substra_path}/data/',
                    f'{substra_path}/conf/:{substra_path}/conf/'],
                 'networks': [network],
                 'depends_on': []
                 },
             },
        'version': '2',
        'networks': {
            network: {'external': True}}
    }

    with open(path, 'w+') as f:
        f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return path


def generate_fixtures_docker(substra_path, fixtures_path, network):

    specs = {
        'name': 'fixtures',
        'filepath': f'/scripts/{fixtures_path}',
    }

    return generate_docker(substra_path, specs, network)


def generate_revoke_docker(substra_path, network):

    specs = {
        'name': 'revoke',
        'filepath': f'/scripts/revoke.py',
    }

    return generate_docker(substra_path, specs, network)


def generate_query_docker(substra_path, network):

    specs = {
        'name': 'query',
        'filepath': f'/scripts/queryUser.py',
    }

    return generate_docker(substra_path, specs, network)

import os


def generate_docker_compose_org(org, substra_path, network):
    try:
        from ruamel import yaml
    except ImportError:
        import yaml

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': f'setup-{org["name"]}',
                                                  'image': 'substra/substra-ca-tools',
                                                  'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup-org.py 2>&1 | tee {substra_path}/data/log/setup-{org["name"]}.log"',
                                                  'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server',
                                                                  'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/fabric/',
                                                                  f'FABRIC_CFG_PATH={substra_path}/data'],
                                                  'volumes': [f'{substra_path}/data:{substra_path}/data',
                                                              f'{substra_path}/conf:{substra_path}/conf',
                                                              './python-scripts:/scripts',
                                                              f'{substra_path}/data/configtx-{org["name"]}.yaml:{substra_path}/data/configtx.yaml',
                                                              f"{substra_path}/conf/{org['name']}/fabric-ca-client-config.yaml:/etc/hyperledger/fabric/fabric-ca-client-config.yaml",
                                                              f"{substra_path}/conf/conf-{org['name']}.json:/{substra_path}/conf/conf-org.json"],
                                                  'networks': [network],
                                                  'depends_on': [],
                                                  },

                                        'run': {'container_name': f'run-{org["name"]}',
                                                'image': 'substra/substra-ca-tools',
                                                'command': f'/bin/bash -c "set -o pipefail;sleep 3;python3 /scripts/run-org.py 2>&1 | tee {substra_path}/data/log/run-{org["name"]}.log"',
                                                'environment': ['GOPATH=/opt/gopath',
                                                                f'FABRIC_CFG_PATH={substra_path}/data'],
                                                'volumes': ['/var/run/docker.sock:/var/run/docker.sock',
                                                            f'{substra_path}/data:{substra_path}/data',
                                                            f'{substra_path}/conf:{substra_path}/conf',
                                                            './python-scripts:/scripts',
                                                            f'{substra_path}/data/configtx-{org["name"]}.yaml:{substra_path}/data/configtx.yaml',
                                                            f"{substra_path}/conf/conf-{org['name']}.json:/{substra_path}/conf/conf-org.json",
                                                            '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'
                                                            ],
                                                'networks': [network],
                                                'depends_on': [],
                                                }
                                        },
                      'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{org["name"]}.yaml')}

    # RCA
    rca = {'container_name': org['ca']['host'],
           'image': 'substra/substra-ca',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'ports': [f"{org['ca']['host_port']}:{org['ca']['port']}"],
           'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
           'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [f'{substra_path}/data:{substra_path}/data',
                       f"{substra_path}/backup/orgs/{org['name']}/rca:/etc/hyperledger/fabric-ca-server/",
                       f"{substra_path}/conf/{org['name']}/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml"
                       ],
           'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
    docker_compose['substra_tools']['setup']['volumes'].append(
        f"{substra_path}/conf/{org['name']}/fabric-ca-client-config.yaml:/root/cas/{org['ca']['host']}/fabric-ca-client-config.yaml")
    docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

    # Peer
    for index, peer in enumerate(org['peers']):
        svc = {'container_name': peer['host'],
               'image': 'substra/substra-ca-peer',
               'restart': 'unless-stopped',
               'command': 'python3 start-peer.py 2>&1',
               'environment': [# https://medium.com/@Alibaba_Cloud/hyperledger-fabric-deployment-on-alibaba-cloud-environment-sigsegv-problem-analysis-and-solutions-9a708313f1a4
                               'GODEBUG=netdns=go+1'],
               'working_dir': '/etc/hyperledger/',
               'ports': [f"{peer['host_port']}:{peer['port']}",
                         f"{peer['host_event_port']}:{peer['event_port']}"],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': [f'{substra_path}/data:{substra_path}/data',
                           f"{substra_path}/data/orgs/{org['name']}/{peer['name']}/fabric/msp/:{org['core']['docker']['msp_config_path']}",
                           f"{substra_path}/backup/orgs/{org['name']}/{peer['name']}/:/var/hyperledger/production/",
                           '/var/run/docker.sock:/host/var/run/docker.sock',
                           f"{substra_path}/conf/{org['name']}/{peer['name']}/core.yaml:/etc/hyperledger/fabric/core.yaml",
                           ],
               'networks': [network],
               'depends_on': ['setup']}

        docker_compose['substra_tools']['run']['depends_on'].append(peer['host'])
        docker_compose['substra_tools']['setup']['volumes'].append(f"{substra_path}/data/orgs/{org['name']}/{peer['name']}/fabric/msp/:{org['core']['docker']['msp_config_path']}/{peer['name']}",)
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


def generate_docker_compose_orderer(orderer, substra_path, network):
    try:
        from ruamel import yaml
    except ImportError:
        import yaml

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': 'setup',
                                                  'image': 'substra/substra-ca-tools',
                                                  'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup-init.py 2>&1 | tee {substra_path}/data/log/setup.log"',
                                                  'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server',
                                                                  f'FABRIC_CFG_PATH={substra_path}/data',
                                                                  'FABRIC_CA_CLIENT_HOME=/etc/hyperledger/fabric'],
                                                  'volumes': [f'{substra_path}/data:{substra_path}/data',
                                                              f"{substra_path}/data/orgs/{orderer['name']}/fabric/msp/:{orderer['local_msp_dir']}",
                                                              f'{substra_path}/data/configtx-init.yaml:{substra_path}/data/configtx.yaml',
                                                              './python-scripts:/scripts',
                                                              f"{substra_path}/conf/{orderer['name']}/fabric-ca-client-config.yaml:/etc/hyperledger/fabric/fabric-ca-client-config.yaml",
                                                              f"{substra_path}/conf/conf-init.json:{substra_path}/conf/conf.json"],
                                                  'networks': [network],
                                                  'depends_on': []}},
                      'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{orderer["name"]}.yaml')}

    # RCA
    rca = {'container_name': orderer['ca']['host'],
           'image': 'substra/substra-ca',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'ports': [f"{orderer['ca']['host_port']}:{orderer['ca']['port']}"],
           'command': '/bin/bash -c "python3 start-root-ca.py 2>&1"',
           'environment': ['FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server'],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [f'{substra_path}/data:{substra_path}/data',
                       f"{substra_path}/backup/orgs/{orderer['name']}/rca:/etc/hyperledger/fabric-ca-server/",
                       f"{substra_path}/conf/{orderer['name']}/fabric-ca-server-config.yaml:/etc/hyperledger/fabric-ca-server/fabric-ca-server-config.yaml"],
           'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(orderer['ca']['host'])
    docker_compose['substra_tools']['setup']['volumes'].append(
        f"{substra_path}/conf/{orderer['name']}/fabric-ca-client-config.yaml:/root/cas/{orderer['ca']['host']}/fabric-ca-client-config.yaml")
    docker_compose['substra_services']['rca'].append((orderer['ca']['host'], rca))

    # ORDERER
    svc = {'container_name': orderer['host'],
           'image': 'substra/substra-ca-orderer',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'command': 'python3 start-orderer.py 2>&1',
           'ports': [f"{orderer['port']}:{orderer['port']}"],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [
               f'{substra_path}/data:{substra_path}/data',
               f"{substra_path}/data/orgs/{orderer['name']}/fabric/msp/:{orderer['local_msp_dir']}",
               f"{substra_path}/backup/orgs/{orderer['name']}/{orderer['name']}:/var/hyperledger/production/orderer",
               f"{substra_path}/conf/{orderer['name']}/core.yaml:/etc/hyperledger/fabric/core.yaml",
               f"{substra_path}/conf/{orderer['name']}/orderer.yaml:/etc/hyperledger/fabric/orderer.yaml"],
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


def generate_docker_compose_test(conf, substra_path, network):
    try:
        from ruamel import yaml
    except ImportError:
        import yaml

    # Docker compose config
    docker_compose = {'substra_test': {
                          'fixtures': {'container_name': 'fixtures',
                                       'image': 'substra/substra-ca-tools',
                                       'command': f"/bin/bash -c \"set -o pipefail; python3 /scripts/{conf['misc']['fixtures_path']} 2>&1 | tee {substra_path}/data/log/fixtures.log\"",
                                       'environment': ['GOPATH=/opt/gopath'],
                                       'volumes': [f'{substra_path}/data:{substra_path}/data',
                                                   f'{substra_path}/conf:{substra_path}/conf',
                                                   './python-scripts:/scripts',
                                                   '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                       'networks': ['substra'],
                                       'depends_on': ['run']},
                          'queryUser': {'container_name': 'queryUser',
                                        'image': 'substra/substra-ca-tools',
                                        'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/queryUser.py 2>&1 | tee {substra_path}/data/log/queryUser.log"',
                                        'environment': ['GOPATH=/opt/gopath'],
                                        'volumes': [f'{substra_path}data:{substra_path}/data',
                                                    f'{substra_path}/conf:{substra_path}/conf',
                                                    './python-scripts:/scripts'],
                                        'networks': ['substra'],
                                        'depends_on': ['run']},
                          'revoke': {'container_name': 'revoke',
                                     'image': 'substra/substra-ca-tools',
                                     'command': f'/bin/bash -c "set -o pipefail; python3 /scripts/revoke.py 2>&1 | tee {substra_path}/data/log/revoke.log"',
                                     'environment': ['GOPATH=/opt/gopath'],
                                     'volumes': [f'{substra_path}/data:{substra_path}/data',
                                                 f'{substra_path}/conf:{substra_path}/conf',
                                                 './python-scripts:/scripts',
                                                 '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode'],
                                     'networks': ['substra'],
                                     'depends_on': ['fixtures']}},
                      'path': os.path.join(substra_path, 'dockerfiles', 'docker-compose-test.yaml')}

    # Create all services along to conf

    COMPOSITION = {'services': {}, 'version': '2', 'networks': {network: {'external': True}}}

    for name, dconfig in docker_compose['substra_test'].items():
        COMPOSITION['services'][name] = dconfig

    with open(docker_compose['path'], 'w+') as f:
        f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose

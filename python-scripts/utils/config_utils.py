import os
import json

from .common_utils import create_directory

from yaml import load, dump, FullLoader

dir_path = os.path.dirname(os.path.realpath(__file__))

SUBSTRA_PATH = '/substra'


def create_ca_server_config(org):
    # For org, create a config file from template
    stream = open(os.path.join(dir_path, '../../templates/fabric-ca-server-config.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    # override template here
    yaml_data['tls']['certfile'] = org['tls']['certfile']

    yaml_data['ca']['name'] = org['ca']['name']
    yaml_data['ca']['certfile'] = org['ca']['certfile']
    # yaml_data['ca']['keyfile'] = org['ca']['keyfile']

    yaml_data['csr']['cn'] = org['csr']['cn']
    yaml_data['csr']['hosts'] += org['csr']['hosts']

    yaml_data['registry']['identities'][0]['name'] = org['users']['bootstrap_admin']['name']
    yaml_data['registry']['identities'][0]['pass'] = org['users']['bootstrap_admin']['pass']

    filename = org['ca']['server-config-path']
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_ca_client_config(org):
    # For org, create a config file from template
    stream = open(os.path.join(dir_path, '../../templates/fabric-ca-client-config.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    # override template here
    # https://hyperledger-fabric-ca.readthedocs.io/en/release-1.2/users-guide.html#enabling-tls
    yaml_data['tls']['certfiles'] = org['ca']['certfile']

    yaml_data['caname'] = org['ca']['name']

    yaml_data['csr']['cn'] = org['csr']['cn']
    yaml_data['csr']['hosts'] += org['csr']['hosts']

    yaml_data['url'] = org['ca']['url']

    filename = org['ca']['client-config-path']
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_configtx(orderers, orgs, filename):

    stream = open(os.path.join(dir_path, '../../templates/configtx.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    # override template here

    yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Addresses'] = [f"{x['host']}:{x['port']['internal']}" for x in orderers]

    configtx_orderers = [{
        'Name': x['name'],
        'ID': x['msp_id'],
        'MSPDir': f"{x['users']['admin']['home']}/msp",
    } for x in orderers]

    configtx_orgs = [{
        'Name': x['name'],
        'ID': x['msp_id'],
        'MSPDir': f"{x['users']['admin']['home']}/msp",
        'AnchorPeers': [{
            'Host': peer['host'],
            'Port': peer['port']['internal']
        } for peer in x['peers'] if peer['anchor']]
    } for x in orgs]

    yaml_data['Organizations'] = configtx_orderers + configtx_orgs

    yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Organizations'] = configtx_orderers
    yaml_data['Profiles']['OrgsOrdererGenesis']['Consortiums']['SampleConsortium']['Organizations'] = configtx_orgs
    yaml_data['Profiles']['OrgsChannel']['Application']['Organizations'] = configtx_orgs

    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_core_peer_config(org):
    for peer in org['peers']:
        stream = open(os.path.join(dir_path, '../../templates/core.yaml'), 'r')
        yaml_data = load(stream, Loader=FullLoader)

        # override template here

        yaml_data['peer']['id'] = peer['host']
        yaml_data['peer']['address'] = f"{peer['host']}:{peer['port']['internal']}"
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
        yaml_data['peer']['gossip']['externalEndpoint'] = f"{peer['host']}:{peer['port']['internal']}"
        yaml_data['peer']['gossip']['skipHandshake'] = 'true'

        yaml_data['vm']['endpoint'] = 'unix:///host/var/run/docker.sock'
        yaml_data['vm']['docker']['hostConfig']['NetworkMode'] = 'net_substra'

        create_directory(peer['docker_core_dir'])
        filename = f"{peer['docker_core_dir']}/core.yaml"
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_orderer_config(orderer, genesis_bloc_file):
    stream = open(os.path.join(dir_path, '../../templates/orderer.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

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
    yaml_data['General']['GenesisFile'] = genesis_bloc_file
    yaml_data['General']['LocalMSPID'] = orderer['msp_id']
    yaml_data['General']['LocalMSPDir'] = orderer['local_msp_dir']

    yaml_data['Debug']['BroadcastTraceDir'] = orderer['broadcast_dir']

    filename = orderer['config-path']
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))

    stream = open(os.path.join(dir_path, '../../templates/core.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    # override template here

    yaml_data['peer']['id'] = orderer['host']
    yaml_data['peer']['address'] = f"{orderer['host']}:{orderer['port']['internal']}"
    yaml_data['peer']['localMspId'] = orderer['msp_id']
    yaml_data['peer']['mspConfigPath'] = orderer['users']['admin']['home'] + '/msp'

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
    yaml_data['peer']['gossip']['externalEndpoint'] = f"{orderer['host']}:{orderer['port']['internal']}"
    yaml_data['peer']['gossip']['skipHandshake'] = 'true'

    yaml_data['vm']['endpoint'] = 'unix:///host/var/run/docker.sock'
    yaml_data['vm']['docker']['hostConfig']['NetworkMode'] = 'net_substra'

    filename = f"/substra/conf/{orderer['name']}/core.yaml"
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_fabric_ca_peer_config(org):
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
        json.dump(peer_conf, open(filename, 'w+'), indent=4)


def create_substrabac_config(org, orderer):

    dir_path = f"{SUBSTRA_PATH}/conf/{org['service']['name']}/substrabac"
    create_directory(dir_path)

    filename = f"{SUBSTRA_PATH}/conf/{org['service']['name']}/substrabac/conf.json"
    # select what need substrabac conf
    peer = org['service']['peers'][0]
    res = {
        'name': org['service']['name'],
        'signcert': org['service']['users']['user']['home'] + '/msp/signcerts/cert.pem',
        'core_peer_mspconfigpath': org['service']['users']['user']['home'] + '/msp',
        'channel_name': org['misc']['channel_name'],
        'chaincode_name': org['misc']['chaincode_name'],
        'chaincode_version': org['misc']['chaincode_version'],
        'peer': {
            'name': peer['name'],
            'host': peer['host'],
            'port': peer['host_port']['external'],
            'docker_port': peer['port']['internal'],
            'docker_core_dir': peer['docker_core_dir'],
            'clientKey': peer['tls']['clientKey'],
            'clientCert': peer['tls']['clientCert'],
        },
        'orderer': {
            'name': orderer['name'],
            'host': orderer['host'],
            'port': orderer['port']['external'],
            'ca': orderer['ca']['certfile'],
        }
    }
    json.dump(res, open(filename, 'w+'), indent=4)

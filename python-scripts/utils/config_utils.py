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
    yaml_data['csr']['names'] = org['csr']['names']

    yaml_data['registry']['identities'][0]['name'] = org['users']['bootstrap_admin']['name']
    yaml_data['registry']['identities'][0]['pass'] = org['users']['bootstrap_admin']['pass']
    yaml_data['affiliations'] = org['ca']['affiliations']

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
    yaml_data['csr']['names'] = org['csr']['names']

    yaml_data['url'] = org['ca']['url']

    filename = org['ca']['client-config-path']
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_configtx(org, filename, raft=True):

    stream = open(os.path.join(dir_path, '../../templates/configtx.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    # override template here

    configtx_org = {
        'Name': org['name'],
        'ID': org['msp_id'],
        'MSPDir': f"{org['users']['admin']['home']}/msp",
    }

    if 'orderers' in org:
        yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Addresses'] = [f"{x['host']}:{x['port']['internal']}" for x in org['orderers']]
        yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['Organizations'] = [configtx_org]

        # Raft
        if raft:
            yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['OrdererType'] = 'etcdraft'
            yaml_data['Profiles']['OrgsOrdererGenesis']['Orderer']['EtcdRaft'] = {'Consenters': [
                {'Host': x['host'],
                 'Port': x['port']['internal'],
                 'ClientTLSCert':f"{x['tls']['dir']['internal']}/{x['tls']['client']['dir']}/{x['tls']['client']['cert']}",
                 'ServerTLSCert': f"{x['tls']['dir']['internal']}/{x['tls']['server']['dir']}/{x['tls']['server']['cert']}"}

                for x in org['orderers']]
            }

    if 'peers' in org:
        configtx_org['AnchorPeers'] = [{
            'Host': peer['host'],
            'Port': peer['port']['internal']
        } for peer in org['peers'] if peer['anchor']]

        yaml_data['Profiles']['OrgsOrdererGenesis']['Consortiums']['SampleConsortium']['Organizations'] = [configtx_org]
        yaml_data['Profiles']['OrgsChannel']['Application']['Organizations'] = [configtx_org]

    yaml_data['Organizations'] = [configtx_org]

    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_core_config(org, peer):
    stream = open(os.path.join(dir_path, '../../templates/core.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    tls_server_dir = peer['tls']['dir']['internal']
    tls_client_dir = f"{peer['tls']['dir']['external']}/{peer['tls']['client']['dir']}"

    # override template here

    yaml_data['peer']['id'] = peer['host']
    yaml_data['peer']['address'] = f"{peer['host']}:{peer['port']['internal']}"
    yaml_data['peer']['localMspId'] = org['msp_id']

    yaml_data['peer']['mspConfigPath'] = f'{org["core_dir"]["internal"]}/msp'

    yaml_data['peer']['tls']['cert']['file'] = f"{tls_server_dir}/{peer['tls']['server']['cert']}"
    yaml_data['peer']['tls']['key']['file'] = f"{tls_server_dir}/{peer['tls']['server']['key']}"
    yaml_data['peer']['tls']['clientCert']['file'] = f"{tls_client_dir}/{peer['tls']['client']['cert']}"
    yaml_data['peer']['tls']['clientKey']['file'] = f"{tls_client_dir}/{peer['tls']['client']['key']}"
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

    peer_core = f'/{SUBSTRA_PATH}/conf/%s/%s' % (org['name'], peer['name'])
    create_directory(peer_core)
    filename = f"{peer_core}/core.yaml"
    with open(filename, 'w+') as f:
        f.write(dump(yaml_data, default_flow_style=False))


def create_peer_config(org):
    for peer in org['peers']:
        create_core_config(org, peer)


def create_orderer_config(orderer_conf):

    org = orderer_conf

    genesis_bloc_file = orderer_conf['misc']['genesis_bloc_file']
    stream = open(os.path.join(dir_path, '../../templates/orderer.yaml'), 'r')
    yaml_data = load(stream, Loader=FullLoader)

    for orderer in org['orderers']:
        tls_server_dir = orderer['tls']['dir']['internal']
        tls_client_dir = f"{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}"

        # override template here
        yaml_data['General']['TLS']['Certificate'] = f"{tls_server_dir}/{orderer['tls']['server']['cert']}"
        yaml_data['General']['TLS']['PrivateKey'] = f"{tls_server_dir}/{orderer['tls']['server']['key']}"
        yaml_data['General']['TLS']['Enabled'] = 'true'
        # passing this to true triggers a SSLV3_ALERT_BAD_CERTIFICATE when querying
        # from the py sdk if peer clientCert/clientKey is not set correctly
        yaml_data['General']['TLS']['ClientAuthRequired'] = 'true'
        yaml_data['General']['TLS']['RootCAs'] = [org['ca']['certfile']]
        yaml_data['General']['TLS']['ClientRootCAs'] = [org['ca']['certfile']]

        yaml_data['General']['ListenAddress'] = '0.0.0.0'
        yaml_data['General']['GenesisMethod'] = 'file'
        yaml_data['General']['GenesisFile'] = genesis_bloc_file
        yaml_data['General']['LocalMSPID'] = org['msp_id']
        yaml_data['General']['LocalMSPDir'] = f"{org['core_dir']['internal']}/msp"

        yaml_data['Debug']['BroadcastTraceDir'] = org['broadcast_dir']

        dir = f'{SUBSTRA_PATH}/conf/{org["name"]}/{orderer["name"]}'
        create_directory(dir)
        filename = f"{dir}/orderer.yaml"
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))

        stream = open(os.path.join(dir_path, '../../templates/core.yaml'), 'r')
        yaml_data = load(stream, Loader=FullLoader)

        # Create core.yaml config for being able to use peer binary for orderer org
        create_core_config(org, orderer)


def create_substrabac_config(org, orderer_conf):

    dir_path = f"{SUBSTRA_PATH}/conf/{org['name']}/substrabac"
    create_directory(dir_path)

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])

    orderer = orderer_conf['orderers'][0]

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    filename = f"{SUBSTRA_PATH}/conf/{org['name']}/substrabac/conf.json"

    res = {
        'name': org['name'],
        'signcert': org['users']['user']['home'] + '/msp/signcerts/cert.pem',
        'core_peer_mspconfigpath': org['users']['user']['home'] + '/msp',
        'channel_name': org['misc']['channel_name'],
        'chaincode_name': org['misc']['chaincode_name'],
        'chaincode_version': org['misc']['chaincode_version'],
        'client': {
            'name': org['service']['users']['user']['name'],
            'org': org['service']['name'],
            'state_store': '/tmp/hfc-cvs',
            'key_path': org['service']['users']['user']['home'] + '/msp/keystore/*',
            'cert_path': org['service']['users']['user']['home'] + '/msp/signcerts/cert.pem',
            'msp_id': org['service']['msp_id']
        },
        'peer': {
            'name': peer['name'],
            'host': peer['host'],
            'port': peer['port']['external'],
            'docker_port': peer['port']['internal'],
            'docker_core_dir': peer_core,
            'tlsCACerts': tls_peer_client_dir + '/' + peer['tls']['client']['ca'],
            'clientCert': tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
            'clientKey': tls_peer_client_dir + '/' + peer['tls']['client']['key'],
            'grpcOptions': {
                'grpc-max-send-message-length': 15,
                'grpc.ssl_target_name_override': peer['host']
            }
        },
        'orderer': {
            'name': orderer['name'],
            'host': orderer['host'],
            'port': orderer['port']['external'],
            'ca': tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
            'grpcOptions': {
                'grpc-max-send-message-length': 15,
                'grpc.ssl_target_name_override': orderer['host']
            }
        }
    }
    json.dump(res, open(filename, 'w+'), indent=4)

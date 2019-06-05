import asyncio

import json
import os
import subprocess
import glob
from shutil import copyfile

from subprocess import call, check_output
from hfc.fabric import Client
from hfc.fabric.orderer import Orderer
from hfc.fabric.organization import create_org
from hfc.fabric.peer import Peer
from hfc.fabric.transaction.tx_context import TXContext
from hfc.fabric.user import create_user
from hfc.util import utils
from hfc.util.keyvaluestore import FileKeyValueStore

cli = Client()
cli._state_store = FileKeyValueStore('/tmp/kvs/')

dir_path = os.path.dirname(os.path.realpath(__file__))

def set_env_variables(fabric_cfg_path, msp_dir):

    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir
    os.environ['FABRIC_LOGGING_SPEC'] = 'info'


def clean_env_variables():
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']
    del os.environ['FABRIC_LOGGING_SPEC']


def set_tls_env_variables(node):

    tls_client_dir = node['tls']['dir']['external'] + '/' + node['tls']['client']['dir']
    tls_server_dir = node['tls']['dir']['external'] + '/' + node['tls']['server']['dir']

    os.environ['CORE_PEER_TLS_ENABLED'] = 'true'
    os.environ['CORE_PEER_TLS_ROOTCERT_FILE'] = tls_server_dir + '/' + node['tls']['server']['ca']
    os.environ['CORE_PEER_TLS_CERT_FILE'] = tls_server_dir + '/' + node['tls']['server']['cert']
    os.environ['CORE_PEER_TLS_KEY_FILE'] = tls_server_dir + '/' + node['tls']['server']['key']

    os.environ['CORE_PEER_TLS_CLIENTAUTHREQUIRED'] = 'true'
    os.environ['CORE_PEER_TLS_CLIENTCERT_FILE'] = tls_client_dir + '/' + node['tls']['client']['cert']
    os.environ['CORE_PEER_TLS_CLIENTKEY_FILE'] = tls_client_dir + '/' + node['tls']['client']['key']
    os.environ['CORE_PEER_TLS_CLIENTROOTCAS_FILES'] = tls_client_dir + '/' + node['tls']['client']['ca']


def clean_tls_env_variables():
    del os.environ['CORE_PEER_TLS_ENABLED']
    del os.environ['CORE_PEER_TLS_ROOTCERT_FILE']
    del os.environ['CORE_PEER_TLS_CERT_FILE']
    del os.environ['CORE_PEER_TLS_KEY_FILE']

    del os.environ['CORE_PEER_TLS_CLIENTAUTHREQUIRED']
    del os.environ['CORE_PEER_TLS_CLIENTCERT_FILE']
    del os.environ['CORE_PEER_TLS_CLIENTKEY_FILE']
    del os.environ['CORE_PEER_TLS_CLIENTROOTCAS_FILES']


def generateChannelArtifacts(conf):
    print(f"Generating channel configuration transaction at {conf['misc']['channel_tx_file']}", flush=True)

    call(['configtxgen',
          '-profile', 'OrgsChannel',
          '-outputCreateChannelTx', conf['misc']['channel_tx_file'],
          '-channelID', conf['misc']['channel_name']])

    print(f"Generating anchor peer update transaction for {conf['name']} at {conf['anchor_tx_file']}", flush=True)

    call(['configtxgen',
          '-profile', 'OrgsChannel',
          '-outputAnchorPeersUpdate', conf['anchor_tx_file'],
          '-channelID', conf['misc']['channel_name'],
          '-asOrg', conf['name']])


# the signer of the channel creation transaction must have admin rights for one of the consortium orgs
# https://stackoverflow.com/questions/45726536/peer-channel-creation-fails-in-hyperledger-fabric
def createChannel(conf, conf_orderer):
    org = conf

    orderer1 = conf_orderer['orderers'][0]

    org_admin = org['users']['admin']

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = os.path.join(org_admin_home, 'msp')


    # save org in cli
    cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

    # register admin in client
    admin_cert_path = os.path.join(org_admin_msp_dir, 'signcerts', 'cert.pem')
    admin_key_path = os.path.join(org_admin_msp_dir, 'keystore', 'key.pem')
    admin = create_user(name=org_admin['name'],
                        org=org['name'],
                        state_store=cli.state_store,
                        msp_id=org['mspid'],
                        cert_path=admin_cert_path,
                        key_path=admin_key_path)
    cli._organizations[org['name']]._users.update({org_admin['name']: admin})

    tls_orderer_client_dir = os.path.join(orderer1['tls']['dir']['external'], orderer1['tls']['client']['dir'])
    orderer = Orderer(orderer1['name'],
                      endpoint=f"{orderer1['host']}:{orderer1['port']['internal']}",
                      tls_ca_cert_file=os.path.join(tls_orderer_client_dir, orderer1['tls']['client']['ca']),
                      client_cert_file=os.path.join(tls_orderer_client_dir, orderer1['tls']['client']['cert']),
                      client_key_file=os.path.join(tls_orderer_client_dir, orderer1['tls']['client']['key']),
                      # opts=(('grpc.ssl_target_name_override', orderer1['host']),)
                      )

    cli._orderers.update({orderer1['name']: orderer})

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.channel_create(
        orderer,
        conf['misc']['channel_name'],
        admin,
        config_tx=conf['misc']['channel_tx_file']))


def peersJoinChannel(conf, conf_orderer):
    print(f"Join channel {[x['name'] for x in conf['peers']]} ...", flush=True)

    channel_name = conf['misc']['channel_name']

    if conf['name'] not in cli.organizations:
        cli._organizations.update({conf['name']: create_org(conf['name'], conf, cli.state_store)})

    # add channel on cli
    if not cli.get_channel(channel_name):
        cli._channels.update({channel_name: cli.new_channel(channel_name)})

    for peer in conf['peers']:
        tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])

        # add peer in cli
        p = Peer(endpoint=f"{peer['host']}:{peer['port']['internal']}",
                 tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                 client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                 client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
        cli._peers.update({peer['name']: p})

    org_admin = conf['users']['admin']

    requestor = cli.get_user(conf['name'], org_admin['name'])
    if not requestor:
        org_admin_home = conf['users']['admin']['home']
        org_admin_msp_dir = os.path.join(org_admin_home, 'msp')

        # register admin in client
        admin_cert_path = os.path.join(org_admin_msp_dir, 'signcerts', 'cert.pem')
        admin_key_path = os.path.join(org_admin_msp_dir, 'keystore', 'key.pem')
        requestor = create_user(name=org_admin['name'],
                                org=conf['name'],
                                state_store=cli.state_store,
                                msp_id=conf['mspid'],
                                cert_path=admin_cert_path,
                                key_path=admin_key_path)
        cli._organizations[conf['name']]._users.update({org_admin['name']: requestor})

    # add orderer organization
    if conf_orderer['name'] not in cli.organizations:
        cli._organizations.update({conf_orderer['name']: create_org(conf_orderer['name'], conf_orderer, cli.state_store)})

    # add orderer admin
    orderer_org_admin = conf_orderer['users']['admin']
    orderer_org_admin_home = orderer_org_admin['home']
    orderer_org_admin_msp_dir = os.path.join(orderer_org_admin_home, 'msp')
    orderer_admin_cert_path = os.path.join(orderer_org_admin_msp_dir, 'signcerts', 'cert.pem')
    orderer_admin_key_path = os.path.join(orderer_org_admin_msp_dir, 'keystore', 'key.pem')
    orderer_admin = create_user(name=orderer_org_admin['name'],
                                org=conf_orderer['name'],
                                state_store=cli.state_store,
                                msp_id=conf_orderer['mspid'],
                                cert_path=orderer_admin_cert_path,
                                key_path=orderer_admin_key_path)
    cli._organizations[conf_orderer['name']]._users.update({orderer_org_admin['name']: orderer_admin})

    # add real orderer from orderer organization
    for o in conf_orderer['orderers']:
        orderer = cli.get_orderer(o['name'])
        if not orderer:
            tls_orderer_client_dir = os.path.join(o['tls']['dir']['external'], o['tls']['client']['dir'])
            orderer = Orderer(o['name'],
                              endpoint=f"{o['host']}:{o['port']['internal']}",
                              tls_ca_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['ca']),
                              client_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['cert']),
                              client_key_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['key']),
                              # opts=(('grpc.ssl_target_name_override', o['host']),)
                              )

            cli._orderers.update({o['name']: orderer})

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.channel_join(
        requestor=requestor,
        channel_name=conf['misc']['channel_name'],
        peers=[x['name'] for x in conf['peers']],
        orderer=orderer,
        orderer_admin=orderer_admin
    ))


def getChannelConfigBlockWithPeer(org, conf_orderer):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])

    orderer = conf_orderer['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call([
        'peer',
        'channel',
        'fetch',
        'config',
        org['misc']['channel_block'],
        '-c', org['misc']['channel_name'],
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
        '--tls',
        '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
        '--clientauth',
        '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
        '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
    ])

    # clean env variables
    clean_env_variables()


def createChannelConfig(org, with_anchor=True):
    org_config = check_output(['configtxgen', '-printOrg', org['name']])

    org_config = json.loads(org_config.decode('utf-8'))

    if with_anchor:
        # Add Anchor peer
        peer = org['peers'][0]
        org_config['values']['AnchorPeers'] = {'mod_policy': 'Admins',
                                               'value': {'anchor_peers': [{'host': peer['host'],
                                                                           'port': peer['port']['internal']}]},
                                               'version': '0'}

    return org_config


def createUpdateProposal(conf, org__channel_config, my_channel_config, channel_name):

    # Keep useful part
    json.dump(my_channel_config, open('mychannelconfig.json', 'w'))

    # Add org
    my_channel_config['channel_group']['groups']['Application']['groups'][conf['name']] = org__channel_config
    json.dump(my_channel_config, open('mychannelconfigupdate.json', 'w'))

    # Compute diff
    call(['configtxlator',
          'proto_encode',
          '--input', 'mychannelconfig.json',
          '--type', 'common.Config',
          '--output', 'mychannelconfig.pb'])

    call(['configtxlator',
          'proto_encode',
          '--input', 'mychannelconfigupdate.json',
          '--type', 'common.Config',
          '--output', 'mychannelconfigupdate.pb'])

    call(['configtxlator',
          'compute_update',
          '--channel_id', channel_name,
          '--original', 'mychannelconfig.pb',
          '--updated', 'mychannelconfigupdate.pb',
          '--output', 'compute_update.pb'])

    call(['configtxlator',
          'proto_decode',
          '--input', 'compute_update.pb',
          '--type', 'common.ConfigUpdate',
          '--output', 'compute_update.json'])


    # Prepare proposal
    update = json.load(open('compute_update.json', 'r'))
    proposal = {'payload': {'header': {'channel_header': {'channel_id': channel_name,
                                                          'type': 2}},
                            'data': {'config_update': update}}}

    json.dump(proposal, open('proposal.json', 'w'))

    config_tx_file = 'proposal.pb'
    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', config_tx_file])
    return config_tx_file


def signAndPushUpdateProposal(orgs, conf_orderer, config_tx_file):
    orderer = conf_orderer['orderers'][0]

    signatures = []
    for org in orgs:
        # Sign
        print(f"Sign update proposal on {org['name']} ...", flush=True)

        # add organization
        if org['name'] not in cli.organizations:
            cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

        org_admin = org['users']['admin']
        org_admin_home = org_admin['home']
        org_admin_msp_dir = os.path.join(org_admin_home, 'msp')

        requestor = cli.get_user(org['name'], org_admin['name'])
        if not requestor:
            # register admin in client
            admin_cert_path = os.path.join(org_admin_msp_dir, 'signcerts', 'cert.pem')
            admin_key_path = os.path.join(org_admin_msp_dir, 'keystore', 'key.pem')
            requestor = create_user(name=org_admin['name'],
                                    org=org['name'],
                                    state_store=cli.state_store,
                                    msp_id=org['mspid'],
                                    cert_path=admin_cert_path,
                                    key_path=admin_key_path)
            cli._organizations[org['name']]._users.update({org_admin['name']: requestor})

        signature = cli.channel_signconfigtx(config_tx_file, requestor)
        signatures.append(signature)
    else:
        # List all signed proposal
        files = glob.glob('./proposal-*.json')
        files.sort(key=os.path.getmtime)
        proposals = [json.load(open(file_path, 'r')) for file_path in files]

        # Take the first signed proposal
        proposal = proposals.pop()

        # Merge signatures into first signed proposal
        for p in proposals:
            proposal['payload']['data']['signatures'].extend(p['payload']['data']['signatures'])
        json.dump(proposal, open('proposal-signed.json', 'w'))

        # Convert it to protobuf
        call(['configtxlator',
              'proto_encode',
              '--input', 'proposal-signed.json',
              '--type', 'common.Envelope',
              '--output', 'proposal-signed.pb'])

        # Push
        print(f"Send update proposal with org: {org['name']}...", flush=True)

        channel_name = org['misc']['channel_name']

        # add real orderer from orderer organization
        for o in conf_orderer['orderers']:
            orderer = cli.get_orderer(o['name'])
            if not orderer:
                tls_orderer_client_dir = os.path.join(o['tls']['dir']['external'], o['tls']['client']['dir'])
                orderer = Orderer(o['name'],
                                  endpoint=f"{o['host']}:{o['port']['internal']}",
                                  tls_ca_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['ca']),
                                  client_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['cert']),
                                  client_key_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['key']),
                                  )

                cli._orderers.update({o['name']: orderer})

        loop = asyncio.get_event_loop()
        loop.run_until_complete(cli.channel_update(
            orderer,
            channel_name,
            requestor,
            config_tx=config_tx_file,
            signatures=signatures))


def generateChannelUpdate(conf, external_orgs, orderer):
    org_channel_config = createChannelConfig(conf)

    my_channel_config_envelope = getChannelConfigBlockWithOrderer(orderer, conf['misc']['channel_name'])
    my_channel_config = my_channel_config_envelope['config']

    config_tx_file = createUpdateProposal(conf, org_channel_config, my_channel_config, conf['misc']['channel_name'])
    signAndPushUpdateProposal(external_orgs, orderer, config_tx_file)


# # the updater of the channel anchor transaction must have admin rights for one of the consortium orgs
# Update the anchor peers
def updateAnchorPeers(org, conf_orderer):
    print(f"Updating anchor peers...", flush=True)

    org_admin = org['users']['admin']
    orderer1 = conf_orderer['orderers'][0]

    channel_name = org['misc']['channel_name']
    orderer = cli.get_orderer(orderer1['name'])
    requestor = cli.get_user(org['name'], org_admin['name'])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.channel_update(
        orderer,
        channel_name,
        requestor,
        config_tx=org['anchor_tx_file']))


def installChainCodeOnPeers(org, chaincode_version):
    print(f"Installing chaincode on {[x['name'] for x in org['peers']]} ...", flush=True)

    chaincode_name = org['misc']['chaincode_name']
    chaincode_path = org['misc']['chaincode_path']
    channel_name = org['misc']['channel_name']

    if org['name'] not in cli.organizations:
        cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

    # add channel on cli
    if not cli.get_channel(channel_name):
        cli._channels.update({channel_name: cli.new_channel(channel_name)})

    for peer in org['peers']:
        if not cli.get_peer(peer['name']):
            tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])

            # add peer in cli
            p = Peer(endpoint=f"{peer['host']}:{peer['port']['internal']}",
                     tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                     client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                     client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
            cli._peers.update({peer['name']: p})

    org_admin = org['users']['admin']
    org_admin_home = org_admin['home']
    org_admin_msp_dir = os.path.join(org_admin_home, 'msp')

    requestor = cli.get_user(org['name'], org_admin['name'])
    if not requestor:
        # register admin in client
        admin_cert_path = os.path.join(org_admin_msp_dir, 'signcerts', 'cert.pem')
        admin_key_path = os.path.join(org_admin_msp_dir, 'keystore', 'key.pem')
        requestor = create_user(name=org_admin['name'],
                                org=org['name'],
                                state_store=cli.state_store,
                                msp_id=org['mspid'],
                                cert_path=admin_cert_path,
                                key_path=admin_key_path)
        cli._organizations[org['name']]._users.update({org_admin['name']: requestor})

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.chaincode_install(
        requestor=requestor,
        peers=[x['name'] for x in org['peers']],
        cc_path=chaincode_path,
        cc_name=chaincode_name,
        cc_version=chaincode_version
    ))


def getChaincodeVersion(org):
    org_admin = org['users']['admin']


    channel_name = org['misc']['channel_name']
    requestor = cli.get_user(org['name'], org_admin['name'])

    for peer in org['peers']:
        if not cli.get_peer(peer['name']):
            tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])
            # add peer in cli
            p = Peer(endpoint=f"{peer['host']}:{peer['port']['internal']}",
                     tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                     client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                     client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
            cli._peers.update({peer['name']: p})

    loop = asyncio.get_event_loop()
    responses = loop.run_until_complete(cli.query_instantiated_chaincodes(
        requestor=requestor,
        channel_name=channel_name,
        peers=[x['name'] for x in org['peers']]
    ))

    # TODO get chaincode which has name like chaincode_name
    version = float(responses[0].chaincodes[0].version)
    return version


def makePolicy(orgs_mspid):
    policy = 'OR('

    for index, org_mspid in enumerate(orgs_mspid):
        if index != 0:
            policy += ','
        policy += '\'' + org_mspid + '.member\''

    policy += ')'
    print('policy: %s' % policy, flush=True)

    return policy


def instanciateChaincode(conf, args=None):

    policy = makePolicy([conf['mspid']])

    org_admin = conf['users']['admin']

    channel_name = conf['misc']['channel_name']
    chaincode_name = conf['misc']['chaincode_name']
    chaincode_version = conf['misc']['chaincode_version']

    requestor = cli.get_user(conf['name'], org_admin['name'])
    loop = asyncio.get_event_loop()

    loop.run_until_complete(cli.chaincode_instantiate(
        requestor=requestor,
        channel_name=channel_name,
        peers=[x['name'] for x in conf['peers']],
        args=args,
        cc_name=chaincode_name,
        cc_version=chaincode_version,
        cc_endorsement_policy=policy,
        wait_for_event=True
    ))


def upgradeChainCode(org, orgs_mspid, chaincode_version, fcn, args=None):
    policy = makePolicy(orgs_mspid)

    for peer in org['peers']:
        tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])

        # add peer in cli
        p = Peer(endpoint=f"{peer['host']}:{peer['port']['internal']}",
                 tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                 client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                 client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
        cli._peers.update({peer['name']: p})

    chaincode_name = org['misc']['chaincode_name']
    channel_name = org['misc']['channel_name']

    org_admin = org['users']['admin']

    requestor = cli.get_user(org['name'], org_admin['name'])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.chaincode_upgrade(
        requestor=requestor,
        channel_name=channel_name,
        peers=[x['name'] for x in org['peers']],
        fcn=fcn,
        args=args,
        cc_name=chaincode_name,
        cc_version=chaincode_version,
        cc_endorsement_policy=policy,
        wait_for_event=True
    ))


def queryChaincodeFromFirstPeerFirstOrg(org, chaincode_version=None):
    org_admin = org['users']['admin']
    peer = org['peers'][0]

    print(f"Try to query chaincode from peer {peer['name']} on org {org['name']} with chaincode version {chaincode_version}", flush=True)

    channel_name = org['misc']['channel_name']
    chaincode_name = org['misc']['chaincode_name']

    requestor = cli.get_user(org['name'], org_admin['name'])

    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(cli.chaincode_query(
        requestor=requestor,
        channel_name=channel_name,
        peers=[peer['name']],
        fcn='queryObjectives',
        args=None,
        cc_name=chaincode_name,
    ))

    return response


def createSystemUpdateProposal(org, conf_orderer):
    # https://console.bluemix.net/docs/services/blockchain/howto/orderer_operate.html?locale=en#orderer-operate

    channel_name = org['misc']['system_channel_name']
    org_config = createChannelConfig(org, with_anchor=False)
    system_channel_config_envelope = getSystemChannelConfigBlock(conf_orderer)
    system_channel_config = system_channel_config_envelope['config']

    json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--input', 'system_channelconfig.json',
          '--type', 'common.Config',
          '--output', 'systemchannelold.block'])

    # Update useful part
    system_channel_config['channel_group']['groups']['Consortiums']['groups']['SampleConsortium']['groups'][
        org['name']] = org_config
    json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--input', 'system_channelconfig.json',
          '--type', 'common.Config',
          '--output', 'systemchannelupdate.block'])

    # Compute update
    call(f'configtxlator compute_update --channel_id {channel_name}'
         f' --original systemchannelold.block'
         f' --updated systemchannelupdate.block'
         f' | '
         f'configtxlator proto_decode --type common.ConfigUpdate'
         f' --output compute_update.json',
         shell=True)

    # Prepare proposal
    update = json.load(open('compute_update.json', 'r'))

    proposal = {'payload': {'header': {'channel_header': {'channel_id': channel_name,
                                                          'type': 2}},
                            'data': {'config_update': update}}}

    json.dump(proposal, open('proposal.json', 'w'))

    config_tx_file = 'proposal.pb'

    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', config_tx_file])

    return config_tx_file


def getSystemChannelConfigBlock(conf_orderer):
    return getChannelConfigBlockWithOrderer(conf_orderer, conf_orderer['misc']['system_channel_name'])


def getChannelConfigBlockWithOrderer(conf, channel_name):
    print('Will getChannelConfigBlockWithOrderer', flush=True)

    # add channel on cli
    if not cli.get_channel(channel_name):
        cli._channels.update({channel_name: cli.new_channel(channel_name)})

    # add orderer organization
    if conf['name'] not in cli.organizations:
        cli._organizations.update({conf['name']: create_org(conf['name'], conf, cli.state_store)})

    # # add orderer admin
    orderer_org_admin = conf['users']['admin']
    orderer_org_admin_home = orderer_org_admin['home']
    orderer_org_admin_msp_dir = os.path.join(orderer_org_admin_home, 'msp')
    orderer_admin_cert_path = os.path.join(orderer_org_admin_msp_dir, 'signcerts', 'cert.pem')
    orderer_admin_key_path = os.path.join(orderer_org_admin_msp_dir, 'keystore', 'key.pem')
    orderer_admin = create_user(name=orderer_org_admin['name'],
                                org=conf['name'],
                                state_store=cli.state_store,
                                msp_id=conf['mspid'],
                                cert_path=orderer_admin_cert_path,
                                key_path=orderer_admin_key_path)
    cli._organizations[conf['name']]._users.update({orderer_org_admin['name']: orderer_admin})

    # add real orderer from orderer organization
    for o in conf['orderers']:
        orderer = cli.get_orderer(o['name'])
        if not orderer:
            tls_orderer_client_dir = os.path.join(o['tls']['dir']['external'], o['tls']['client']['dir'])
            orderer = Orderer(o['name'],
                              endpoint=f"{o['host']}:{o['port']['internal']}",
                              tls_ca_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['ca']),
                              client_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['cert']),
                              client_key_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['key']),
                              )

            cli._orderers.update({o['name']: orderer})

    loop = asyncio.get_event_loop()
    config_envelope = loop.run_until_complete(cli.get_channel_config_with_orderer(
        orderer=orderer,
        requestor=orderer_admin,
        channel_name=channel_name
    ))

    print('got ChannelConfigBlockWithOrderer', flush=True)

    return config_envelope


def signAndPushSystemUpdateProposal(org, config_tx_file):
    print('signAndPushSystemUpdateProposal')

    channel_name = org['misc']['system_channel_name']

    # add channel on cli
    if not cli.get_channel(channel_name):
        cli._channels.update({channel_name: cli.new_channel(channel_name)})

    # add orderer organization
    if org['name'] not in cli.organizations:
        cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

    # add orderer admin
    orderer_org_admin = org['users']['admin']
    orderer_org_admin_home = orderer_org_admin['home']
    orderer_org_admin_msp_dir = os.path.join(orderer_org_admin_home, 'msp')
    orderer_admin_cert_path = os.path.join(orderer_org_admin_msp_dir, 'signcerts', 'cert.pem')
    orderer_admin_key_path = os.path.join(orderer_org_admin_msp_dir, 'keystore', 'key.pem')
    orderer_admin = create_user(name=orderer_org_admin['name'],
                                org=org['name'],
                                state_store=cli.state_store,
                                msp_id=org['mspid'],
                                cert_path=orderer_admin_cert_path,
                                key_path=orderer_admin_key_path)
    cli._organizations[org['name']]._users.update({orderer_org_admin['name']: orderer_admin})

    # add real orderer from orderer organization
    for o in org['orderers']:
        orderer = cli.get_orderer(o['name'])
        if not orderer:
            tls_orderer_client_dir = os.path.join(o['tls']['dir']['external'], o['tls']['client']['dir'])
            orderer = Orderer(o['name'],
                              endpoint=f"{o['host']}:{o['port']['internal']}",
                              tls_ca_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['ca']),
                              client_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['cert']),
                              client_key_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['key']),
                              # opts=(('grpc.ssl_target_name_override', o['host']),)
                              )

            cli._orderers.update({o['name']: orderer})

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.channel_update(
        orderer,
        channel_name,
        orderer_admin,
        config_tx=config_tx_file))

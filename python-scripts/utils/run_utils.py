import json
import os
import time
import subprocess

from subprocess import call, check_output, CalledProcessError

dir_path = os.path.dirname(os.path.realpath(__file__))


def set_env_variables(fabric_cfg_path, msp_dir, tls_dir):

    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir
    os.environ['FABRIC_LOGGING_SPEC'] = 'info'
    os.symlink(tls_dir['external'], tls_dir['internal'])


def clean_env_variables(tls_dir):
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']
    del os.environ['FABRIC_LOGGING_SPEC']
    os.unlink(tls_dir['internal'])


def generateChannelArtifacts(conf):

    print('Generating channel configuration transaction at %(channel_tx_file)s' % {
        'channel_tx_file': conf['misc']['channel_tx_file']}, flush=True)

    call(['configtxgen',
          '-profile', 'OrgsChannel',
          '-outputCreateChannelTx', conf['misc']['channel_tx_file'],
          '-channelID', conf['misc']['channel_name']])

    org = conf
    print('Generating anchor peer update transaction for %(org_name)s at %(anchor_tx_file)s' % {
        'org_name': org['name'],
        'anchor_tx_file': org['anchor_tx_file']
    }, flush=True)

    call(['configtxgen',
          '-profile', 'OrgsChannel',
          '-outputAnchorPeersUpdate', org['anchor_tx_file'],
          '-channelID', conf['misc']['channel_name'],
          '-asOrg', org['name']])


# the signer of the channel creation transaction must have admin rights for one of the consortium orgs
# https://stackoverflow.com/questions/45726536/peer-channel-creation-fails-in-hyperledger-fabric
def createChannel(conf, conf_orderer):

    org = conf

    orderer = conf_orderer['orderers'][0]

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call([
        'peer',
        'channel',
        'create',
        '-c', conf['misc']['channel_name'],
        '--outputBlock', conf['misc']['channel_block'],
        '-f', conf['misc']['channel_tx_file'],
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
        '--tls',
        '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
        '--clientauth',
        '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
        '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
    ])

    # clean env variables
    clean_env_variables(peer_tls_dir)


def joinChannel(conf, peer):
    # peer channel join use signcerts not admincerts, we need to pass CORE_PEER_MSPCONFIGPATH to org admin.
    # peer msp signcert is not an admin, a peer cannot join a channel with its own msp

    org_admin_home = conf['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = conf['misc']['channel_name']
    print('Peer %(peer_host)s is attempting to join channel \'%(channel_name)s\' ...' % {
        'peer_host': peer['host'],
        'channel_name': channel_name
    }, flush=True)

    peer_core = '/substra/conf/%s/%s' % (conf['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    call([
        'peer',
        'channel',
        'join',
        '-b', conf['misc']['channel_block']
    ])

    # clean env variables
    clean_env_variables(peer_tls_dir)


def peersJoinChannel(conf):
    for peer in conf['peers']:
        joinChannel(conf, peer)


def getChannelConfigBlockWithPeer(org, conf_orderer):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    orderer = conf_orderer['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

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
    clean_env_variables(peer_tls_dir)


def createChannelConfig(org, with_anchor=True):

    org_config = check_output(['configtxgen',
                               '-printOrg', org['name']])

    org_config = json.loads(org_config.decode('utf-8'))

    if with_anchor:
        # Add Anchor peer
        peer = org['peers'][0]
        org_config['values']['AnchorPeers'] = {'mod_policy': 'Admins',
                                               'value': {'anchor_peers': [{'host': peer['host'],
                                                                           'port': peer['port']['internal']}]},
                                               'version': '0'}

    return org_config


def createUpdateProposal(conf, org__channel_config, input_block, channel_name):
    call(['configtxlator',
          'proto_decode',
          '--input', input_block,
          '--type', 'common.Block',
          '--output', 'mychannelconfig.json'])

    my_channel_config = json.load(open('mychannelconfig.json', 'r'))

    # Keep useful part
    my_channel_config = my_channel_config['data']['data'][0]['payload']['data']['config']
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
    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', 'proposal.pb'])


def signAndPushUpdateProposal(orgs, conf_orderer, channel_name):
    orderer = conf_orderer['orderers'][0]

    for org in orgs:
        # Sign
        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = org_admin_home + '/msp'

        peer = org['peers'][0]
        peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
        peer_tls_dir = peer['tls']['dir']

        set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

        tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
        tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

        print('Sign update proposal on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

        call(['peer',
              'channel', 'signconfigtx',
              '-f', 'proposal.pb',
              '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
              '--tls',
              '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
              # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
              '--clientauth',
              '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
              '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
              ])

        # clean env variables
        clean_env_variables(peer_tls_dir)
    else:
        # Push
        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = org_admin_home + '/msp'

        peer = org['peers'][0]
        peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
        peer_tls_dir = peer['tls']['dir']

        set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

        tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
        tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

        print('Send update proposal on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

        call(['peer',
              'channel', 'update',
              '-f', 'proposal.pb',
              '-c', channel_name,
              '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
              '--tls',
              '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
              # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
              '--clientauth',
              '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
              '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
              ])

        # clean env variables
        clean_env_variables(peer_tls_dir)


def generateChannelUpdate(conf, conf_externals, orderer):

    org_channel_config = createChannelConfig(conf)
    getChannelConfigBlockWithOrderer(orderer, conf['misc']['channel_name'], 'mychannelconfig.block')

    createUpdateProposal(conf, org_channel_config, 'mychannelconfig.block', conf['misc']['channel_name'])
    external_orgs = [conf_org for conf_org in conf_externals]
    signAndPushUpdateProposal(external_orgs, orderer, conf['misc']['channel_name'])


# # the updater of the channel anchor transaction must have admin rights for one of the consortium orgs
# Update the anchor peers
def updateAnchorPeers(conf, conf_orderer):
    # :warning: for updating anchor peers make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    orderer = conf_orderer['orderers'][0]

    print('Updating anchor peers for %(peer_host)s ...' % {'peer_host': org['peers'][0]['host']}, flush=True)

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call(['peer',
          'channel', 'update',
          '-c', conf['misc']['channel_name'],
          '-f', org['anchor_tx_file'],
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
          '--tls',
          '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--clientauth',
          '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
          '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
          ])

    # clean env variables
    clean_env_variables(peer_tls_dir)


def installChainCode(conf, peer, chaincode_version):
    org_admin_home = conf['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    chaincode_name = conf['misc']['chaincode_name']

    print('Installing chaincode on %(peer_host)s ...' % {'peer_host': peer['host']}, flush=True)

    peer_core = '/substra/conf/%s/%s' % (conf['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    call(['peer',
          'chaincode', 'install',
          '-n', chaincode_name,
          '-v', chaincode_version,
          '-p', 'github.com/hyperledger/chaincode/'])

    # clean env variables
    clean_env_variables(peer_tls_dir)


def installChainCodeOnPeers(conf, chaincode_version):
    for peer in conf['peers']:
        installChainCode(conf, peer, chaincode_version)


def waitForInstantiation(conf, conf_orderer):
    org = conf

    channel_name = conf['misc']['channel_name']

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    orderer = conf_orderer['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    print('Test if chaincode is instantiated on %(PEER_HOST)s ... (timeout 30 seconds)' % {'PEER_HOST': peer['host']},
          flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 30:
        call(['sleep', '1'])
        output = subprocess.run(['peer',
                                 'chaincode', 'list',
                                 '-C', conf['misc']['channel_name'],
                                 '--instantiated',
                                 '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
                                 '--tls',
                                 '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
                                 # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
                                 '--clientauth',
                                  '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
                                  '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
                                 ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        data = output.stdout.decode('utf-8')
        print(data, flush=True)
        split_msg = 'Get instantiated chaincodes on channel %s:' % channel_name
        if split_msg in data and len(data.split(split_msg)[1].replace('\n', '')):
            print(data, flush=True)
            clean_env_variables(peer_tls_dir)
            return True
        print('.', end='', flush=True)

    clean_env_variables(peer_tls_dir)
    return False


def getChaincodeVersion(conf, conf_orderer):
    org = conf

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    orderer = conf_orderer['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    output = subprocess.run(['peer',
                             'chaincode', 'list',
                             '-C', conf['misc']['channel_name'],
                             '--instantiated',
                             '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
                             '--tls',
                             '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
                             # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
                             '--clientauth',
                             '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
                             '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
                             ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    data = output.stdout.decode('utf-8')
    clean_env_variables(peer_tls_dir)
    return float(data.split('Version: ')[-1].split(',')[0])


def makePolicy(orgs_mspid):
    policy = 'OR('

    for index, org_mspid in enumerate(orgs_mspid):
        if index != 0:
            policy += ','
        policy += '\'' + org_mspid + '.member\''

    policy += ')'
    print('policy: %s' % policy, flush=True)

    return policy


def instanciateChainCode(conf, conf_orderer, args):
    policy = makePolicy([conf['msp_id']])

    org_admin_home = conf['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    peer = conf['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (conf['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    orderer = conf_orderer['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    print('Instantiating chaincode on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call(['peer',
          'chaincode', 'instantiate',
          '-C', conf['misc']['channel_name'],
          '-n', conf['misc']['chaincode_name'],
          '-v', conf['misc']['chaincode_version'],
          '-c', args,
          '-P', policy,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
          '--tls',
          '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--clientauth',
          '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
          '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
          ])

    # clean env variables
    clean_env_variables(peer_tls_dir)


def instanciateChaincode(conf, orderer):
    instanciateChainCode(conf, orderer, '{"Args":["init"]}')


def upgradeChainCode(conf, args, conf_orderer, orgs_mspid, chaincode_version):
    policy = makePolicy(orgs_mspid)

    org = conf

    peer = org['peers'][0]
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    orderer = conf_orderer['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir, peer_tls_dir)

    print('Instantiating chaincode on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    tls_peer_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call(['peer',
          'chaincode', 'upgrade',
          '-C', conf['misc']['channel_name'],
          '-n', conf['misc']['chaincode_name'],
          '-v', chaincode_version,
          '-c', args,
          '-P', policy,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
          '--tls',
          '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--clientauth',
          '--certfile', tls_peer_client_dir + '/' + peer['tls']['client']['cert'],
          '--keyfile', tls_peer_client_dir + '/' + peer['tls']['client']['key']
          ])

    # clean env variables
    clean_env_variables(peer_tls_dir)


def chainCodeQueryWith(conf, arg, org, peer):
    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'

    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    peer_tls_dir = peer['tls']['dir']

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_user_msp_dir, peer_tls_dir)

    channel_name = conf['misc']['channel_name']
    chaincode_name = conf['misc']['chaincode_name']

    print('Querying chaincode in the channel \'%(channel_name)s\' on the peer \'%(peer_host)s\' ...' % {
        'channel_name': channel_name,
        'peer_host': peer['host']
    }, flush=True)

    try:
        output = check_output(['peer', 'chaincode', 'query',
                               '-C', channel_name,
                               '-n', chaincode_name,
                               '-c', arg]).decode()
    except CalledProcessError as e:
        output = e.output.decode()
        print('Error:', flush=True)
        print('Output: %s' % output, flush=True)
        # clean env variables
        clean_env_variables(peer_tls_dir)
    else:
        try:
            value = json.loads(output)
        except:
            value = output
        else:
            msg = 'Query of channel \'%(channel_name)s\' on peer \'%(peer_host)s\' was successful' % {
                'channel_name': channel_name,
                'peer_host': peer['host']
            }
            print(msg, flush=True)
            print('Value: %s' % value, flush=True)

        finally:
            # clean env variables
            clean_env_variables(peer_tls_dir)
            return value


def queryChaincodeFromFirstPeerFirstOrg(conf):
    org = conf
    peer = org['peers'][0]

    print('Try to query chaincode from first peer first org before invoke', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith(conf,
                                  '{"Args":["queryObjectives"]}',
                                  org,
                                  peer)
        # data should be null
        print(data, flush=True)
        if data is None:
            print('Correctly initialized', flush=True)
            return True

        print('.', end='', flush=True)

    print('\n/!\ Failed to query chaincode with initialized values', flush=True)
    return False


def createSystemUpdateProposal(org, conf_orderer):

    # https://console.bluemix.net/docs/services/blockchain/howto/orderer_operate.html?locale=en#orderer-operate

    channel_name = org['misc']['system_channel_name']
    channel_block = org['misc']['system_channel_block']
    org_config = createChannelConfig(org, False)

    getSystemChannelConfigBlock(conf_orderer, channel_block)

    call(['configtxlator',
          'proto_decode',
          '--input', channel_block,
          '--type', 'common.Block',
          '--output', 'system_channelconfig.json'])
    system_channel_config = json.load(open('system_channelconfig.json', 'r'))

    # Keep useful part
    system_channel_config = system_channel_config['data']['data'][0]['payload']['data']['config']
    json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--input', 'system_channelconfig.json',
          '--type', 'common.Config',
          '--output', 'systemchannelold.block'])

    # Update useful part
    system_channel_config['channel_group']['groups']['Consortiums']['groups']['SampleConsortium']['groups'][org['name']] = org_config
    json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--input', 'system_channelconfig.json',
          '--type', 'common.Config',
          '--output', 'systemchannelupdate.block'])

    # Compute update
    call(' '.join(['configtxlator',
                   'compute_update',
                   '--channel_id', channel_name,
                   '--original', 'systemchannelold.block',
                   '--updated', 'systemchannelupdate.block',
                   ' | ', 'configtxlator',
                   'proto_decode',
                   '--type', 'common.ConfigUpdate',
                   '--output', 'compute_update.json']),
         shell=True)

    # Prepare proposal
    update = json.load(open('compute_update.json', 'r'))

    # print(json.dumps(update, indent=4))
    proposal = {'payload': {'header': {'channel_header': {'channel_id': channel_name,
                                                          'type': 2}},
                            'data': {'config_update': update}}}

    json.dump(proposal, open('proposal.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', 'proposal.pb'])


def getSystemChannelConfigBlock(conf, block_name):
    getChannelConfigBlockWithOrderer(conf, conf['misc']['system_channel_name'], block_name)


def getChannelConfigBlockWithOrderer(org, channel_name, block_name):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    orderer_admin_home = org['users']['admin']['home']
    orderer_admin_msp_dir = orderer_admin_home + '/msp'

    orderer = org['orderers'][0]
    orderer_core = '/substra/conf/%s/%s' % (org['name'], orderer['name'])
    orderer_tls_dir = orderer['tls']['dir']

    set_env_variables(orderer_core, orderer_admin_msp_dir, orderer_tls_dir)

    tls_peer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call([
        'peer',
        'channel',
        'fetch',
        'config',
        block_name,
        '-c', channel_name,
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
        '--tls',
        '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
        '--clientauth',
        '--certfile', tls_peer_client_dir + '/' + orderer['tls']['client']['cert'],
        '--keyfile', tls_peer_client_dir + '/' + orderer['tls']['client']['key']
    ])

    # clean env variables
    clean_env_variables(orderer_tls_dir)


def signAndPushSystemUpdateProposal(conf):
    org = conf
    channel_name = conf['misc']['system_channel_name']

    org_admin_home = org['users']['admin']['home']
    orderer_admin_msp_dir = org_admin_home + '/msp'

    orderer = org['orderers'][0]
    orderer_core = '/substra/conf/%s/%s' % (org['name'], orderer['name'])
    orderer_tls_dir = orderer['tls']['dir']

    set_env_variables(orderer_core, orderer_admin_msp_dir, orderer_tls_dir)

    tls_peer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']

    call(['peer',
          'channel', 'update',
          '-f', 'proposal.pb',
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['internal']},
          '--tls',
          '--cafile', tls_orderer_client_dir + '/' + orderer['tls']['client']['ca'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--clientauth',
          '--certfile', tls_peer_client_dir + '/' + orderer['tls']['client']['cert'],
          '--keyfile', tls_peer_client_dir + '/' + orderer['tls']['client']['key']
          ])

    # clean env variables
    clean_env_variables(orderer_tls_dir)

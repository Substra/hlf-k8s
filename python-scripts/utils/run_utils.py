import docker
import json
import os
import time
import subprocess

from subprocess import call, check_output, CalledProcessError

dir_path = os.path.dirname(os.path.realpath(__file__))

client = docker.from_env()


def set_env_variables(fabric_cfg_path, msp_dir):
    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir
    os.environ['FABRIC_LOGGING_SPEC'] = 'debug'


def clean_env_variables():
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']
    del os.environ['FABRIC_LOGGING_SPEC']


# the signer of the channel creation transaction must have admin rights for one of the consortium orgs
# https://stackoverflow.com/questions/45726536/peer-channel-creation-fails-in-hyperledger-fabric
def createChannel(conf, org, peer):

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    call([
        'peer',
        'channel',
        'create',
        '-c', conf['misc']['channel_name'],
        '--outputBlock', conf['misc']['channel_block'],
        '-f', conf['misc']['channel_tx_file'],
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
        '--tls',
        '--clientauth',
        '--cafile', orderer['ca']['certfile'],
        '--keyfile', peer['tls']['clientKey'],
        '--certfile', peer['tls']['clientCert']
    ])

    # clean env variables
    clean_env_variables()


def joinChannel(conf, peer, org):
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = conf['misc']['channel_name']
    print('Peer %(peer_host)s is attempting to join channel \'%(channel_name)s\' ...' % {
        'peer_host': peer['host'],
        'channel_name': channel_name
    }, flush=True)

    # peer channel join use signcerts not admincerts, we need to pass CORE_PEER_MSPCONFIGPATH to org admin.
    # peer msp signcert is not an admin, a peer cannot join a channel with its own msp
    container = client.containers.get(peer['host'])
    container.exec_run('bash -c "export CORE_PEER_MSPCONFIGPATH=%s && peer channel join -b %s"' % (org_admin_msp_dir, conf['misc']['channel_block']))


def peersJoinChannel(conf):
    for org in conf['orgs']:
        for peer in org['peers']:
            joinChannel(conf, peer, org)


def getChannelBlock(conf, org, peer):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    call([
        'peer',
        'channel',
        'fetch',
        '0',
        'mychannel.block',
        '-c', conf['misc']['channel_name'],
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
        '--tls',
        '--clientauth',
        '--cafile', orderer['ca']['certfile'],
        '--keyfile', peer['tls']['clientKey'],
        '--certfile', peer['tls']['clientCert']
    ])

    # clean env variables
    clean_env_variables()


def getChannelConfigBlock(conf, org, peer, block_name):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    call([
        'peer',
        'channel',
        'fetch',
        'config',
        block_name,
        '-c', conf['misc']['channel_name'],
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
        '--tls',
        '--clientauth',
        '--cafile', orderer['ca']['certfile'],
        '--keyfile', peer['tls']['clientKey'],
        '--certfile', peer['tls']['clientCert']
    ])

    # clean env variables
    clean_env_variables()


def createChannelConfig(org, with_anchor=True):

    org_config = check_output(['configtxgen',
                               '-printOrg', org['name']])

    org_config = json.loads(org_config.decode('utf-8'))

    if with_anchor:
        # Add Anchor peer
        peer = org['peers'][0]
        org_config['values']['AnchorPeers'] = {'mod_policy': 'Admins',
                                               'value': {'anchor_peers': [{'host': peer['host'],
                                                                           'port': peer['port']}]},
                                               'version': '0'}

    return org_config


def createUpdateProposal(org, org_config, conf, input_block, channel_name):
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
    my_channel_config['channel_group']['groups']['Application']['groups'][org['name']] = org_config
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


def signAndPushUpdateProposal(conf, org_type='orgs'):
    orderer = conf['orderers'][0]

    for org in conf[org_type]:

        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = org_admin_home + '/msp'
        orderer = conf['orderers'][0]
        peer = org['peers'][0]

        set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

        print('Sign update proposal on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

        call(['peer',
              'channel', 'signconfigtx',
              '-f', 'proposal.pb',
              '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
              '--tls',
              '--clientauth',
              '--cafile', orderer['ca']['certfile'],
              # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
              '--keyfile', peer['tls']['clientKey'],
              '--certfile', peer['tls']['clientCert']
              ])

        # clean env variables
        clean_env_variables()
    else:
        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = org_admin_home + '/msp'
        orderer = conf['orderers'][0]
        peer = org['peers'][0]

        set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

        print('Send update proposal on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

        call(['peer',
              'channel', 'update',
              '-f', 'proposal.pb',
              '-c', conf['misc']['channel_name'],
              '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
              '--tls',
              '--clientauth',
              '--cafile', orderer['ca']['certfile'],
              # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
              '--keyfile', peer['tls']['clientKey'],
              '--certfile', peer['tls']['clientCert']
              ])

        # clean env variables
        clean_env_variables()


def generateChannelUpdate(conf, conf_global):

    for org in conf['orgs']:
        org_config = createChannelConfig(org)
        getChannelConfigBlock(conf_global,
                              conf_global['orgs'][0],
                              conf_global['orgs'][0]['peers'][0],
                              'mychannelconfig.block')

        createUpdateProposal(org, org_config, conf, 'mychannelconfig.block', conf['misc']['channel_name'])
        signAndPushUpdateProposal(conf_global)


# # the updater of the channel anchor transaction must have admin rights for one of the consortium orgs
# Update the anchor peers
def updateAnchorPeers(conf):
    # :warning: for updating anchor peers make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    for org in conf['orgs']:
        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = org_admin_home + '/msp'
        orderer = conf['orderers'][0]

        peer = org['peers'][0]
        print('Updating anchor peers for %(peer_host)s ...' % {'peer_host': org['peers'][0]['host']}, flush=True)

        # update config path for using right core.yaml and right msp dir
        set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

        call(['peer',
              'channel', 'update',
              '-c', conf['misc']['channel_name'],
              '-f', org['anchor_tx_file'],
              '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
              '--tls',
              '--clientauth',
              '--cafile', orderer['ca']['certfile'],
              # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
              '--keyfile', peer['tls']['clientKey'],
              '--certfile', peer['tls']['clientCert']
              ])

        # clean env variables
        clean_env_variables()


def installChainCode(conf, org, peer):
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    chaincode_name = conf['misc']['chaincode_name']
    chaincode_version = conf['misc']['chaincode_version']

    print('Installing chaincode on %(peer_host)s ...' % {'peer_host': peer['host']}, flush=True)

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    call(['peer',
          'chaincode', 'install',
          '-n', chaincode_name,
          '-v', chaincode_version,
          '-p', 'github.com/hyperledger/chaincode/'])

    # clean env variables
    clean_env_variables()


def installChainCodeOnPeers(conf):
    for org in conf['orgs']:
        for peer in org['peers']:
            installChainCode(conf, org, peer)


def waitForInstantiation(conf):
    org = conf['orgs'][0]
    peer = org['peers'][0]

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    print('Test if chaincode is instantiated on %(PEER_HOST)s ... (timeout 15 seconds)' % {'PEER_HOST': peer['host']},
          flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 30:
        call(['sleep', '1'])
        output = subprocess.run(['peer',
                                 'chaincode', 'list',
                                 '-C', conf['misc']['channel_name'],
                                 '--instantiated',
                                 '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
                                 '--tls',
                                 '--clientauth',
                                 '--cafile', orderer['tls']['certfile'],
                                 # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
                                 '--keyfile', peer['tls']['clientKey'],
                                 '--certfile', peer['tls']['clientCert']
                                 ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        data = output.stdout.decode('utf-8')
        print(data, flush=True)
        split_msg = 'Get instantiated chaincodes on channel mychannel:'
        if split_msg in data and len(data.split(split_msg)[1].replace('\n', '')):
            print(data, flush=True)
            clean_env_variables()
            return True
        print('.', end='', flush=True)

    clean_env_variables()
    return False


def makePolicy(conf):
    policy = 'OR('

    for index, org in enumerate(conf['orgs']):
        if index != 0:
            policy += ','
        policy += '\'' + org['msp_id'] + '.member\''

    policy += ')'
    print('policy: %s' % policy, flush=True)

    return policy


def instanciateChainCode(conf, args, org, peer):
    policy = makePolicy(conf)

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    print('Instantiating chaincode on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    call(['peer',
          'chaincode', 'instantiate',
          '-C', conf['misc']['channel_name'],
          '-n', conf['misc']['chaincode_name'],
          '-v', conf['misc']['chaincode_version'],
          '-c', args,
          '-P', policy,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['ca']['certfile'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--keyfile', peer['tls']['clientKey'],
          '--certfile', peer['tls']['clientCert']
          ])

    # clean env variables
    clean_env_variables()


def instanciateChaincode(conf):
    org = conf['orgs'][0]
    peer = org['peers'][0]
    instanciateChainCode(conf, '{"Args":["init"]}', org, peer)


def upgradeChainCode(conf, args, org, peer):
    policy = makePolicy(conf)

    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers'][0]

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_admin_msp_dir)

    print('Instantiating chaincode on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    call(['peer',
          'chaincode', 'upgrade',
          '-C', conf['misc']['channel_name'],
          '-n', conf['misc']['chaincode_name'],
          '-v', conf['misc']['chaincode_version'],
          '-c', args,
          '-P', policy,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['ca']['certfile'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--keyfile', peer['tls']['clientKey'],
          '--certfile', peer['tls']['clientCert']
          ])

    # clean env variables
    clean_env_variables()


def chainCodeQueryWith(conf, arg, org, peer):
    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_user_msp_dir)

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
        clean_env_variables()
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
            clean_env_variables()
            return value


def queryChaincodeFromFirstPeerFirstOrg(conf):
    org = conf['orgs'][0]
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


def createSystemUpdateProposal(conf, channel_name):

    # https://console.bluemix.net/docs/services/blockchain/howto/orderer_operate.html?locale=en#orderer-operate

    org = conf['orgs'][0]
    org_config = createChannelConfig(org, False)

    system_channelblock = 'systemchannel.block'

    getSystemChannelConfigBlock(conf, channel_name, system_channelblock)

    call(['configtxlator',
          'proto_decode',
          '--input', system_channelblock,
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


def getSystemChannelConfigBlock(conf, channel_name, block_name):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    orderer = conf['orderers'][0]
    orderer_admin_home = orderer['users']['admin']['home']
    orderer_admin_msp_dir = orderer_admin_home + '/msp'
    orderer_core = '/substra/conf/%s' % orderer['name']

    set_env_variables(orderer_core, orderer_admin_msp_dir)

    call([
        'peer',
        'channel',
        'fetch',
        'config',
        block_name,
        '-c', channel_name,
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
        '--tls',
        '--clientauth',
        '--cafile', orderer['ca']['certfile'],
        '--keyfile', orderer['tls']['clientKey'],
        '--certfile', orderer['tls']['clientCert']
    ])

    # clean env variables
    clean_env_variables()


def signAndPushSystemUpdateProposal(conf, channel_name):
    orderer = conf['orderers'][0]
    orderer_admin_home = orderer['users']['admin']['home']
    orderer_admin_msp_dir = orderer_admin_home + '/msp'
    orderer_core = '/substra/conf/%s' % orderer['name']

    set_env_variables(orderer_core, orderer_admin_msp_dir)

    call(['peer',
          'channel', 'update',
          '-f', 'proposal.pb',
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['ca']['certfile'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--keyfile', orderer['tls']['clientKey'],
          '--certfile', orderer['tls']['clientCert']
          ])

    # clean env variables
    clean_env_variables()

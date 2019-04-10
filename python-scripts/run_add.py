import docker
import json
import os

from subprocess import call, check_output
from run import peersJoinChannel, installChainCodeOnPeers, queryChaincodeFromFirstPeerFirstOrg, makePolicy
dir_path = os.path.dirname(os.path.realpath(__file__))

client = docker.from_env()


def set_env_variables(fabric_cfg_path, msp_dir):
    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir


def clean_env_variables():
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


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
        '--logging-level=DEBUG',
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
        '--logging-level=DEBUG',
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
          '--logging-level', 'DEBUG',
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


def createConfig(org):

    org_config = check_output(['configtxgen',
                               '-printOrg', org['name']])

    org_config = json.loads(org_config.decode('utf-8'))

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
              '--logging-level', 'DEBUG',
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
        org_config = createConfig(org)
        getChannelConfigBlock(conf_global,
                              conf_global['orgs'][0],
                              conf_global['orgs'][0]['peers'][0],
                              'mychannelconfig.block')

        createUpdateProposal(org, org_config, conf, 'mychannelconfig.block', conf['misc']['channel_name'])
        signAndPushUpdateProposal(conf_global)


def run(conf, conf_global):

    generateChannelUpdate(conf, conf_global)

    org = conf['orgs'][0]

    # getChannelBlock(conf, org, org['peers'][0])
    peersJoinChannel(conf)

    # Upgrade policy
    org = conf_global['orgs'][0]
    peer = org['peers'][0]
    conf_global['orgs'] += conf['orgs']
    conf_global['misc']['chaincode_version'] = '2.0'

    # Install chaincode on peer in each org
    installChainCodeOnPeers(conf_global)

    upgradeChainCode(conf_global, '{"Args":["init"]}', org, peer)

    if queryChaincodeFromFirstPeerFirstOrg(conf):
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":
    conf_path = '/substra/conf/conf-add.json'
    conf = json.load(open(conf_path, 'r'))

    conf_path = '/substra/conf/conf.json'
    conf_global = json.load(open(conf_path, 'r'))

    run(conf, conf_global)

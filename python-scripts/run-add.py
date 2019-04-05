import docker
import json
import os

from subprocess import call
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


def run(conf, conf_global):

    org = conf['orgs'][0]

    getChannelBlock(conf, org, org['peers'][0])
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

import base64
import copy
import json
import os
import time
import subprocess

import requests

from confOrg3 import conf
from conf import conf as conf2
from subprocess import call, check_output, STDOUT, CalledProcessError, Popen


def getChannelBlock(org_name, peer):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf2['orderers']['orderer']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting the one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    call([
        'peer',
        'channel',
        'fetch',
        '0',
        # 'config',
        'mychannel.block',
        '--logging-level=DEBUG',
        '-c', 'mychannel',
        '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
        '--tls',
        '--clientauth',
        '--cafile', orderer['tls']['certfile'],
        '--keyfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',
        '--certfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt'
    ])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


# Enroll as a fabric admin and join the channel
def joinChannel(peer, org_name):
    # :warning: for joining channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'
    channel_name = conf['misc']['channel_name']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']

    # update mspconfigpath for getting one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    # configAdminLocalMSP(org)
    print('Peer %(peer_host)s is attempting to join channel \'%(channel_name)s\' ...' % {
        'peer_host': peer['host'],
        'channel_name': channel_name}, flush=True)

    call(['peer',
          'channel', 'join',
          '--logging-level=DEBUG',
          '-b', channel_name + '.block'
          ])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def peersJoinChannel():
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        for peer in org['peers']:
            joinChannel(peer, org_name)


# Update the anchor peers
def updateAnchorPeers():
    # :warning: for updating anchor peers make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        org_admin_home = org['admin_home']
        org_admin_msp_dir = org_admin_home + '/msp'
        orderer = conf2['orderers']['orderer']

        peer = org['peers'][0]
        print('Updating anchor peers for %(peer_host)s ...' % {'peer_host': org['peers'][0]['host']}, flush=True)

        # update config path for using right core.yaml
        os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']

        # update mspconfigpath for getting the one in /data
        os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

        call(['peer',
              'channel', 'update',
              '-c', conf['misc']['channel_name'],
              '-f', org['anchor_tx_file'],
              '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
              '--tls',
              '--clientauth',
              '--cafile', orderer['tls']['certfile'],
              # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
              '--keyfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',  # for orderer
              '--certfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt'
              ])

        # clean env variables
        del os.environ['FABRIC_CFG_PATH']
        del os.environ['CORE_PEER_MSPCONFIGPATH']


def installChainCode(org_name, peer):
    # :warning: for installing chaincode make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'

    chaincode_name = conf['misc']['chaincode_name']

    print('Installing chaincode on %(peer_host)s ...' % {'peer_host': peer['host']}, flush=True)

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']

    # update mspconfigpath for getting one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    call(['peer',
          'chaincode', 'install',
          '-n', chaincode_name,
          '-v', '1.0',
          '-p', 'github.com/hyperledger/chaincode/'])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def installChainCodeOnPeers():
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        for id_peer in range(len(org['peers'])):
            peer = org['peers'][id_peer]
            installChainCode(org_name, peer)


def makePolicy():
    policy = 'OR('

    for index, org_name in enumerate(conf['orgs']):
        if index != 0:
            policy += ','
        policy += '\'' + conf['orgs'][org_name]['org_msp_id'] + '.member\''

    policy += ')'
    print('policy: %s' % policy, flush=True)

    return policy


def instanciateChainCode(args, org_name, peer):
    # :warning: for instanciating chaincode make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    policy = makePolicy()

    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf2['orderers']['orderer']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']

    # update mspconfigpath for getting one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    print('Instantiating chaincode on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    call(['peer',
          'chaincode', 'instantiate',
          '--logging-level=DEBUG',
          '-C', conf['misc']['channel_name'],
          '-n', conf['misc']['chaincode_name'],
          '-v', '1.0',
          '-c', args,
          '-P', policy,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['tls']['certfile'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--keyfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',  # for orderer
          '--certfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt'
          ])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def instanciateChainCodeOnPeers():
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        for id_peer in range(len(org['peers'])):
            peer = org['peers'][id_peer]
            instanciateChainCode('{"Args":["init"]}', org_name, peer)


def chainCodeQueryWith(arg, org_name, peer):
    org = conf['orgs'][org_name]
    org_user_home = org['user_home']
    org_user_msp_dir = org_user_home + '/msp'

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']

    # update mspconfigpath for getting one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_user_msp_dir

    def clean_env_variables():
        del os.environ['FABRIC_CFG_PATH']
        del os.environ['CORE_PEER_MSPCONFIGPATH']

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
        print(output)
    else:
        print(output, flush=True)
        try:
            value = output.split(': ')[1].replace('\n', '')
            value = json.loads(value)
        except:
            value = output
        else:
            msg = 'Query of channel \'%(channel_name)s\' on peer \'%(peer_host)s\' was successful' % {
                'channel_name': channel_name,
                'peer_host': peer['host']
            }
            print(msg, flush=True)
            print(value, flush=True)

        finally:
            # clean env variables
            clean_env_variables()
            return value


def queryChaincodeFromFirstPeer():
    org_name = 'org3'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    print('Try to query chaincode from first peer third org', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
                                  org_name,
                                  peer)
        if isinstance(data, list) and len(data) > 0:
            print('Correctly added and got', flush=True)
            return True

        print('.', end='', flush=True)

    print('/!\ Failed to query chaincode with added value', flush=True)
    return False


def queryChaincodeFromFirstPeerAfterInvoke():
    org_name = 'owkin'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    print('Try to query chaincode from first peer first org after invoke', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
                                  org_name,
                                  peer)
        # data should not be null
        print(data, flush=True)
        if isinstance(data, list) and len(data) > 0:
            print('Correctly added and got', flush=True)
            return True

        print('.', end='', flush=True)

    print('\n/!\ Failed to query chaincode after invoke', flush=True)
    return False


def queryChaincodeFromSecondPeer():
    org_name = 'org3'
    org = conf['orgs'][org_name]
    peer = org['peers'][1]

    print('Try to query chaincode from second peer third org', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
                                  org_name,
                                  peer)
        if isinstance(data, list) and len(data) > 0:
            print('Correctly added and got', flush=True)
            return True

        print('.', end='', flush=True)

    print('/!\ Failed to query chaincode with added value', flush=True)
    return False


def invokeChainCode(args, org, peer):
    org_name = org['org_name']
    org_user_home = org['user_home']
    org_user_msp_dir = org_user_home + '/msp'
    orderer = conf2['orderers']['orderer']
    channel_name = conf['misc']['channel_name']
    chaincode_name = conf['misc']['chaincode_name']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']

    # update mspconfigpath for getting one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_user_msp_dir

    print('Sending invoke transaction to %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    output = subprocess.run(['peer',
                  'chaincode', 'invoke',
                  '-C', channel_name,
                  '-n', chaincode_name,
                  '-c', args,
                  '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
                  '--tls',
                  '--clientauth',
                  '--cafile', orderer['tls']['certfile'],
                  '--keyfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',
                  '--certfile', '/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt'
                  ],
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)

    data = output.stderr.decode('utf-8')

    print(data, flush=True)

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']

    try:
        # Format it to get generated key
        data = data.split('result: status:')[1].split('\n')[0].split('payload:')[1].replace(' ', '').replace('"', '')
    except:
        return ''
    else:
        return data


def run():
    res = True

    getChannelBlock('org3', conf['orgs']['org3']['peers'][0])
    peersJoinChannel()
    # updateAnchorPeers()
    installChainCodeOnPeers()

    # Instantiate chaincode on the 1st peer of the 2nd org
    # instanciateChainCodeOnPeers()

    # wait chaincode is instanciated and initialized before querying it
    print('Wait 3sec until chaincode is instanciated and initialized before querying it', flush=True)
    call(['sleep', '3'])

    # Query chaincode from the 1st peer of the 1st org
    res = res and queryChaincodeFromFirstPeer()

    # Query chaincode on 2nd peer of 2nd org
    res = res and queryChaincodeFromSecondPeer()

    if res:
        print('Congratulations! The tests ran successfully.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Test Failed.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":
    run()

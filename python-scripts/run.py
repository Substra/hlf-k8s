import base64
import copy
import json
import os
import time
import subprocess

import requests

from conf import conf
from subprocess import call, check_output, STDOUT, CalledProcessError, Popen


def createChannel(org_name, peer):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers']['orderer']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting the one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    call([
        'peer',
        'channel',
        'create',
        '--logging-level=DEBUG',
        '-c', 'mychannel',
        '-f', '/data/channel.tx',
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
        orderer = conf['orderers']['orderer']

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


def installChainCodeOnFirstPeers():
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        peer = org['peers'][0]
        installChainCode(org_name, peer)


def installChainCodeOnSecondPeerSecondOrg():
    org_name = 'chu-nantes'
    org = conf['orgs'][org_name]
    peer = org['peers'][1]
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
    orderer = conf['orderers']['orderer']

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


def instanciateChaincodeFirstPeerSecondOrg():
    org_name = 'chu-nantes'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]
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


def queryChaincodeFromFirstPeerFirstOrg():
    org_name = 'owkin'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    print('Try to query chaincode from first peer first org before invoke', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
                                  org_name,
                                  peer)
        # data should be null
        print(data, flush=True)
        if data is None:
            print('Correctly initialized', flush=True)
            return True

        print('.', end='', flush=True)

    print('\n/!\ Failed to query chaincode with initialized values', flush=True)
    return False


def queryChaincodeFromFirstPeerFirstOrgAfterInvoke():
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
        if isinstance(data, list) and len(data) == 2:
            print('Correctly added and got', flush=True)
            return True

        print('.', end='', flush=True)

    print('\n/!\ Failed to query chaincode after invoke', flush=True)
    return False


def queryChaincodeFromSecondPeerSecondOrg():
    org_name = 'chu-nantes'
    org = conf['orgs'][org_name]
    peer = org['peers'][1]

    print('Try to query chaincode from second peer second org', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
                                  org_name,
                                  peer)
        if isinstance(data, list) and len(data) == 2:
            print('Correctly added and got', flush=True)
            return True

        print('.', end='', flush=True)

    print('/!\ Failed to query chaincode with added value', flush=True)
    return False


def invokeChainCode(args, org, peer):
    org_name = org['org_name']
    org_user_home = org['user_home']
    org_user_msp_dir = org_user_home + '/msp'
    orderer = conf['orderers']['orderer']
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


def invokeChaincodeFirstPeers():
    org_name = 'chu-nantes'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    # should fail
    args = '{"Args":["registerDataset","liver slide"]}'
    invokeChainCode(args, org, peer)

    # create dataset with chu-nantes org
    args = '{"Args":["registerDataset","ISIC 2018","ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994","http://127.0.0.1:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener","Images","f969e52d66a40c8f0fa00733baecf2d1b4c48d676c41186865f15032bf62f096","http://127.0.0.1:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description","","all"]}'
    dataset_chunantes = invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for dataset on chu-nantes to be created', flush=True)
    call(['sleep', '3'])

    # register train data on dataset chu nantes (will take dataset creator as worker)
    args = '{"Args":["registerData","62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9","%s","100","false"]}' % dataset_chunantes
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for train data to be created', flush=True)
    call(['sleep', '3'])

    # create dataset and test data on owkin
    #######
    # /!\ #
    #######

    org_name = 'owkin'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    #######
    # /!\ #
    #######

    # create dataset with owkin org
    args = '{"Args":["registerDataset","ISIC 2019","a8b7c235abb9a93742e336bd76ff7cd8ecc49f612e5cf6ea506dc10f4fd6b6f0","http://127.0.0.1:8000/dataset/a8b7c235abb9a93742e336bd76ff7cd8ecc49f612e5cf6ea506dc10f4fd6b6f0/opener","Images","15863c2af1fcfee9ca6f61f04be8a0eaaf6a45e4d50c421788d450d198e580f1","http://127.0.0.1:8000/dataset/a8b7c235abb9a93742e336bd76ff7cd8ecc49f612e5cf6ea506dc10f4fd6b6f0/description","","all"]}'
    dataset_owkin = invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for dataset on owkin to be created', flush=True)
    call(['sleep', '3'])

    # register test data on dataset on owkin (will take dataset creator as worker)
    args = '{"Args":["registerData","e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1, 4b5152871b181d10ee774c10458c064c70710f4ba35938f10c0b7aa51f7dc010", "%s","100","true"]}' % dataset_owkin
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for test data to be created', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["queryDatasets"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for datasets to be queried', flush=True)
    call(['sleep', '3'])

    # create challenge
    args = '{"Args":["registerChallenge", "MSI classification", "eb0295d98f37ae9e95102afae792d540137be2dedf6c4b00570ab1d1f355d033", "http://127.0.0.1:8000/challenge/eb0295d98f37ae9e95102afae792d540137be2dedf6c4b00570ab1d1f355d033/description", "accuracy", "750f622262854341bd44f55c1018949e9c119606ef5068bd7d137040a482a756", "http://127.0.0.1:8000/challenge/eb0295d98f37ae9e95102afae792d540137be2dedf6c4b00570ab1d1f355d033/metrics", "e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1", "all"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for challenge to be created', flush=True)
    call(['sleep', '3'])


    # go back to chu-nantes
    #######
    # /!\ #
    #######

    org_name = 'chu-nantes'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    #######
    # /!\ #
    #######

    # create challenge
    args = '{"Args":["registerChallenge", "Skin Lesion Classification Challenge", "d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f", "http://127.0.0.1:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/description", "macro-average recall", "750f622262854341bd44f55c1018949e9c119606ef5068bd7d137040a482a756", "http://127.0.0.1:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/metrics", "4b5152871b181d10ee774c10458c064c70710f4ba35938f10c0b7aa51f7dc010", "all"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for challenge to be created', flush=True)
    call(['sleep', '3'])

    # create algo
    args = '{"Args":["registerAlgo","Logistic regression","6dcbfcf29146acd19c6a2997b2e81d0cd4e88072eea9c90bbac33f0e8573993f","http://127.0.0.1:8001/algo/6dcbfcf29146acd19c6a2997b2e81d0cd4e88072eea9c90bbac33f0e8573993f/file","124a0425b746d7072282d167b53cb6aab3a31bf1946dae89135c15b0126ebec3","http://127.0.0.1:8001/algo/6dcbfcf29146acd19c6a2997b2e81d0cd4e88072eea9c90bbac33f0e8573993f/description","eb0295d98f37ae9e95102afae792d540137be2dedf6c4b00570ab1d1f355d033","all"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for algo to be created', flush=True)
    call(['sleep', '3'])

    # create second algo
    args = '{"Args":["registerAlgo","Logistic regression 2","094f479d77a2c71e643fe3efefe3fb1ee371e3100912379b70ad2eea2295bca4","http://127.0.0.1:8001/algo/094f479d77a2c71e643fe3efefe3fb1ee371e3100912379b70ad2eea2295bca4/file","8bf47bdf04cdfd37a4158e5c552863464b63b740ce2342bc7291ed528c4dad0e","http://127.0.0.1:8001/algo/094f479d77a2c71e643fe3efefe3fb1ee371e3100912379b70ad2eea2295bca4/description","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for algo to be created', flush=True)
    call(['sleep', '3'])

    # query data of the dataset in chu nantes
    args = '{"Args":["queryDatasetData","%s"]}' % dataset_chunantes
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for dataset Data queried', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["queryTraintuples"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for traintuples to be queried', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["createTraintuple","094f479d77a2c71e643fe3efefe3fb1ee371e3100912379b70ad2eea2295bca4","","62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9"]}'
    traintuple = invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for traintuple to be created', flush=True)
    call(['sleep', '3'])

    # recreation of traintuple should fail
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for second traintuple to be created and yield fail', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["logStartTrainTest","' + traintuple + '", "training"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for traintuple status to be updated to `training`', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["queryTraintuples"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for traintuples to be queried', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["logSuccessTrain","' + traintuple + '","10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568, http://127.0.0.1:8001/model/10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568/file","62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a:0.90, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9:0.91","no error, ah ah ah"]}'
    invokeChainCode(args, org, peer)

    print(
        'Sleeping 3 seconds for traintuple status to be updated to `trained`, endModel to be set and performances on train data to be set',
        flush=True)
    call(['sleep', '3'])

    # go back to owkin for test data
    #######
    # /!\ #
    #######

    org_name = 'owkin'
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    #######
    # /!\ #
    #######

    # back to wokin who own test data on this traintuple related dataset
    args = '{"Args":["logStartTrainTest","' + traintuple + '","testing"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for traintuple status to be updated to `testing`', flush=True)
    call(['sleep', '3'])

    args = '{"Args":["logSuccessTest","' + traintuple + '","e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1:0.90, 4b5152871b181d10ee774c10458c064c70710f4ba35938f10c0b7aa51f7dc010:0.91","0.99","still no error, suprah ah ah"]}'
    invokeChainCode(args, org, peer)

    print('Sleeping 3 seconds for traintuple status to be updated to `done` and performances updated', flush=True)
    call(['sleep', '3'])


def revokeFabricUserAndGenerateCRL(org_name, username):
    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']

    print(
        'Revoking the user \'%(username)s\' of the organization \'%(org_name)s\' with Fabric CA Client home directory set to %(org_admin_home)s and generating CRL ...' % {
            'username': username,
            'org_name': org_name,
            'org_admin_home': org_admin_home
        }, flush=True)

    call(['fabric-ca-client',
          'revoke', '-d',
          '-c', '/data/orgs/' + org_name + '/admin/fabric-ca-client-config.yaml',
          '--revoke.name', username,
          '--gencrl'])


def fetchConfigBlock(org_name, peer):
    org = conf['orgs'][org_name]

    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'
    channel_name = conf['misc']['channel_name']
    orderer = conf['orderers']['orderer']
    config_block_file = conf['misc']['config_block_file']

    print('Fetching the configuration block of the channel \'%s\'' % channel_name, flush=True)

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting the one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    call(['peer', 'channel', 'fetch', 'config', config_block_file,
          '-c', channel_name,
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


def createConfigUpdatePayloadWithCRL(org_name):
    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = conf['misc']['channel_name']
    config_block_file = conf['misc']['config_block_file']

    print('Creating config update payload with the generated CRL for the organization \'%s\'' % org_name, flush=True)

    # Start the configtxlator
    # call('configtxlator start &', shell=True)
    proc = Popen('configtxlator start &', shell=True)

    print('Sleeping 5 seconds for configtxlator to start...', flush=True)
    call(['sleep', '5'])

    CTLURL = 'http://127.0.0.1:7059'
    # Convert the config block protobuf to JSON
    r = requests.post(CTLURL + '/protolator/decode/common.Block', data=open(config_block_file, 'rb').read())
    config_block = r.json()

    # Extract the config from the config block
    config = config_block['data']['data'][0]['payload']['data']['config']

    # Update crl in the config json
    updated_config = copy.deepcopy(config)
    with open(org_admin_msp_dir + '/crls/crl.pem', 'rb') as f:
        crl = base64.b64encode(f.read()).decode('utf8')
        updated_config['channel_group']['groups']['Application']['groups'][org_name]['values']['MSP']['value'][
            'config']['revocation_list'] = [crl]

    # Create the config diff protobuf
    r = requests.post(CTLURL + '/protolator/encode/common.Config', json=config, stream=True)
    config_pb = None
    if r.status_code == 200:
        config_pb = r.content
    else:
        print(r.text, flush=True)

    r = requests.post(CTLURL + '/protolator/encode/common.Config', json=updated_config, stream=True)
    updated_config_pb = None
    if r.status_code == 200:
        updated_config_pb = r.content
    else:
        print(r.text, flush=True)

    r = requests.post(CTLURL + '/configtxlator/compute/update-from-configs', data={'channel': channel_name},
                      files={'original': config_pb, 'updated': updated_config_pb})
    config_update_pb = None
    if r.status_code == 200:
        config_update_pb = r.content
    else:
        print(r.text, flush=True)

    # call(['curl', '-X', 'POST', '--data-binary', '@config.json', CTLURL + '/protolator/encode/common.Config', '>', '/tmp/config.pb'])
    # call(['curl', '-X', 'POST', '--data-binary', '@updated_config.json', CTLURL + '/protolator/encode/common.Config', '>', '/tmp/updated_config.pb'])
    # call(['curl', '-X', 'POST', '-F', 'original=@config.pb', '-F', 'updated=@updated_config.pb', CTLURL + '/configtxlator/compute/update-from-configs', '-F', 'channel=' + channel_name, '>', '/tmp/config_update.pb'])

    # Convert the config diff protobuf to JSON
    r = requests.post(CTLURL + '/protolator/decode/common.ConfigUpdate', data=config_update_pb, stream=True)
    config_update = {}
    if r.status_code == 200:
        config_update = r.json()
    else:
        print(r.text, flush=True)
    # call(['curl', '-X', 'POST', '--data-binary', '@config_update.pb', CTLURL + '/protolator/decode/common.ConfigUpdate', '>', '/tmp/config_update.json'])

    # Create envelope protobuf container config diff to be used in the "peer channel update" command to update the channel configuration block
    config_update_as_envelope = {
        'payload': {
            'header': {
                'channel_header': {
                    'channel_id': channel_name,
                    'type': 2,
                }
            },
            'data': {
                'config_update': config_update
            }
        }
    }

    r = requests.post(CTLURL + '/protolator/encode/common.Envelope', json=config_update_as_envelope)
    if r.status_code == 200:
        with open(conf['misc']['config_update_envelope_file'], 'wb') as f:
            for chunk in r:
                f.write(chunk)
    else:
        print(r.text, flush=True)
    #   echo '{"payload":{"header":{"channel_header":{"channel_id":"'"${CHANNEL_NAME}"'", "type":2}},"data":{"config_update":'$(cat config_update.json)'}}}' > config_update_as_envelope.json
    #   curl -X POST --data-binary @config_update_as_envelope.json $CTLURL/protolator/encode/common.Envelope > $CONFIG_UPDATE_ENVELOPE_FILE

    # Stop configtxlator
    proc.kill()


def updateConfigBlock(org_name, peer):
    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = conf['misc']['channel_name']
    orderer = conf['orderers']['orderer']
    config_update_envelope_file = conf['misc']['config_update_envelope_file']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting the one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    print('Updating the configuration block of the channel \'%s\'' % channel_name, flush=True)
    call(['peer', 'channel', 'update',
          '-f', config_update_envelope_file,
          '-c', channel_name,
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


def queryAsRevokedUser(arg, org_name, peer, username):
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

    print(
        'Querying the chaincode in the channel \'%(CHANNEL_NAME)s\' on the peer \'%(PEER_HOST)s\' as revoked user \'%(USER_NAME)s\' ...' % {
            'CHANNEL_NAME': channel_name,
            'PEER_HOST': peer['host'],
            'USER_NAME': username,
        }, flush=True)

    starttime = int(time.time())

    # Continue to poll until we get a successful response or reach QUERY_TIMEOUT
    while int(time.time()) - starttime < 15:  # QUERY_TIMEOUT
        call(['sleep', '1'])

        try:
            check_output(['peer', 'chaincode', 'query',
                          '-C', channel_name,
                          '-n', chaincode_name, '-c', arg],
                         stderr=STDOUT).decode()
        except CalledProcessError as e:
            output = e.output.decode()
            # uncomment for debug
            if 'access denied' in output:
                print(
                    'Expected error occurred when the revoked user \'%(username)s\' queried the chaincode in the channel \'%(channel_name)s\'\n' % {
                        'channel_name': channel_name,
                        'username': username,
                    }, flush=True)
                # clean env variables
                clean_env_variables()
                return True
        else:
            print('.', flush=True, end='')

    err_msg = 'The revoked user %(username)s should have failed to query the chaincode in the channel \'%(channel_name)s\'' % {
        'channel_name': channel_name,
        'username': username
    }
    print(err_msg, flush=True)
    # clean env variables
    clean_env_variables()
    return False


def revokeFirstOrgUser():
    # Revoke the user and generate CRL using admin's credentials
    org_name = 'owkin'
    org = conf['orgs'][org_name]
    username = org['users']['user']['name']
    peer = org['peers'][0]

    revokeFabricUserAndGenerateCRL('owkin', username)

    # Fetch config block
    fetchConfigBlock(org_name, peer)

    # Create config update envelope with CRL and update the config block of the channel
    createConfigUpdatePayloadWithCRL('owkin')
    updateConfigBlock(org_name, peer)

    return queryAsRevokedUser('{"Args":["queryObjects", "problem"]}', org_name, peer, username)


def run():
    res = True

    createChannel('owkin', conf['orgs']['owkin']['peers'][0])
    peersJoinChannel()
    updateAnchorPeers()

    # Install chaincode on the 1st peer in each org
    installChainCodeOnFirstPeers()

    # Instantiate chaincode on the 1st peer of the 2nd org
    instanciateChaincodeFirstPeerSecondOrg()

    # wait chaincode is instanciated and initialized before querying it
    print('Wait 3sec until chaincode is instanciated and initialized before querying it', flush=True)
    call(['sleep', '3'])

    # Query chaincode from the 1st peer of the 1st org
    res = res and queryChaincodeFromFirstPeerFirstOrg()

    # Invoke chaincode with 1st peers of each org
    invokeChaincodeFirstPeers()

    # Query chaincode from the 1st peer of the 1st org after Invoke
    res = res and queryChaincodeFromFirstPeerFirstOrgAfterInvoke()

    # Install chaincode on 2nd peer of 2nd org
    installChainCodeOnSecondPeerSecondOrg()

    # wait chaincode is instanciated and initialized before querying it
    print('Wait 3sec until chaincode is installed before querying it', flush=True)
    call(['sleep', '3'])

    # Query chaincode on 2nd peer of 2nd org
    res = res and queryChaincodeFromSecondPeerSecondOrg()

    # Revoke first org user
    # res = res and revokeFirstOrgUser()

    if res:
        print('Congratulations! The tests ran successfully.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Test Failed.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":
    run()

import docker
import json
import os
import time
import subprocess

from subprocess import call, check_output, CalledProcessError

dir_path = os.path.dirname(os.path.realpath(__file__))

client = docker.from_env()

# the signer of the channel creation transaction must have admin rights for one of the consortium orgs
# https://stackoverflow.com/questions/45726536/peer-channel-creation-fails-in-hyperledger-fabric
def createChannel(conf, org_name, peer):
    # :warning: for creating channel make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf['orgs'][org_name]
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers']['orderer']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = peer['docker_core_dir']
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

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
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def joinChannel(conf, peer):

    channel_name = conf['misc']['channel_name']
    print('Peer %(peer_host)s is attempting to join channel \'%(channel_name)s\' ...' % {
        'peer_host': peer['host'],
        'channel_name': channel_name
    }, flush=True)

    container = client.containers.get(peer['host'])
    container.exec_run('bash -c "peer channel join -b %s"' % conf['misc']['channel_block'])

def peersJoinChannel(conf):
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        for peer in org['peers']:
            joinChannel(conf, peer)


# # the updater of the channel anchor transaction must have admin rights for one of the consortium orgs
# Update the anchor peers
def updateAnchorPeers(conf):
    # :warning: for updating anchor peers make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = org_admin_home + '/msp'
        orderer = conf['orderers']['orderer']

        peer = org['peers'][0]
        print('Updating anchor peers for %(peer_host)s ...' % {'peer_host': org['peers'][0]['host']}, flush=True)

        # update config path for using right core.yaml
        os.environ['FABRIC_CFG_PATH'] = peer['docker_core_dir']
        # update mspconfigpath for getting the one in /substra/data/
        os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

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
        del os.environ['FABRIC_CFG_PATH']
        del os.environ['CORE_PEER_MSPCONFIGPATH']


def installChainCode(conf, org_name, peer):
    # :warning: for installing chaincode make sure env variables CORE_PEER_MSPCONFIGPATH is correctly set

    org = conf['orgs'][org_name]
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    chaincode_name = conf['misc']['chaincode_name']

    print('Installing chaincode on %(peer_host)s ...' % {'peer_host': peer['host']}, flush=True)

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = peer['docker_core_dir']
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    call(['peer',
          'chaincode', 'install',
          '-n', chaincode_name,
          '-v', '1.0',
          '-p', 'github.com/hyperledger/chaincode/'])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def installChainCodeOnPeers(conf):
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        for peer in org['peers']:
            installChainCode(conf, org_name, peer)


def waitForInstantiation(conf):
    org_name = list(conf['orgs'].keys())[0]
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    org = conf['orgs'][org_name]
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers']['orderer']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = peer['docker_core_dir']
    # update mspconfigpath for getting one in /substra/data/
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    def clean_env_variables():
        del os.environ['FABRIC_CFG_PATH']
        del os.environ['CORE_PEER_MSPCONFIGPATH']

    print('Test if chaincode is instantiated on %(PEER_HOST)s ... (timeout 15 seconds)' % {'PEER_HOST': peer['host']},
          flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 30:
        call(['sleep', '1'])
        output = subprocess.run(['peer',
                                 '--logging-level', 'DEBUG',
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

    for index, org_name in enumerate(conf['orgs']):
        if index != 0:
            policy += ','
        policy += '\'' + conf['orgs'][org_name]['msp_id'] + '.member\''

    policy += ')'
    print('policy: %s' % policy, flush=True)

    return policy

def instanciateChainCode(conf, args, org_name, peer):
    policy = makePolicy(conf)

    org = conf['orgs'][org_name]
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    orderer = conf['orderers']['orderer']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = peer['docker_core_dir']
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    print('Instantiating chaincode on %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']}, flush=True)

    call(['peer',
          'chaincode', 'instantiate',
          '--logging-level', 'DEBUG',
          '-C', conf['misc']['channel_name'],
          '-n', conf['misc']['chaincode_name'],
          '-v', '1.0',
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
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def instanciateChaincode(conf):
    org_name = list(conf['orgs'].keys())[0]
    org = conf['orgs'][org_name]
    peer = org['peers'][0]
    instanciateChainCode(conf, '{"Args":["init"]}', org_name, peer)


def chainCodeQueryWith(conf, arg, org_name, peer):
    org = conf['orgs'][org_name]
    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = peer['docker_core_dir']
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
    org_name = list(conf['orgs'].keys())[0]
    org = conf['orgs'][org_name]
    peer = org['peers'][0]

    print('Try to query chaincode from first peer first org before invoke', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith(conf,
                                  '{"Args":["queryChallenges"]}',
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


def run(conf):
    res = True
    org_chan = list(conf['orgs'].keys())[0]
    createChannel(conf, org_chan, conf['orgs'][org_chan]['peers'][0])
    peersJoinChannel(conf)
    # updateAnchorPeers(conf)
    #
    # # Install chaincode on peer in each org
    # installChainCodeOnPeers(conf)
    #
    # # Instantiate chaincode on the 1st peer of the 2nd org
    # instanciateChaincode(conf)

    # # Wait chaincode is correctly instantiated and initialized
    # res = res and waitForInstantiation(conf)
    #
    # # Query chaincode from the 1st peer of the 1st org
    # res = res and queryChaincodeFromFirstPeerFirstOrg(conf)

    if res:
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":
    conf_path = '/substra/conf/conf.json'

    conf = json.load(open(conf_path, 'r'))

    run(conf)

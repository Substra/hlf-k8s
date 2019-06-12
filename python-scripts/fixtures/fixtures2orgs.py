import asyncio
import glob
import json
import os
import time
import subprocess

from subprocess import call, check_output, CalledProcessError

from hfc.fabric import Client
from hfc.fabric.orderer import Orderer
from hfc.fabric.organization import create_org
from hfc.fabric.peer import Peer
from hfc.fabric.user import create_user
from hfc.util.keyvaluestore import FileKeyValueStore

cli = Client()
cli._state_store = FileKeyValueStore('/tmp/kvs/')

SUBSTRA_PATH = '/substra'

def set_env_variables(fabric_cfg_path, msp_dir):
    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir


def clean_env_variables():
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


# def chainCodeQueryWith(arg, org, peer):
#     org_user_home = org['users']['user']['home']
#     org_user_msp_dir = org_user_home + '/msp'
#
#     peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
#
#     # update config path for using right core.yaml and right msp dir
#     set_env_variables(peer_core, org_user_msp_dir)
#
#     channel_name = conf['misc']['channel_name']
#     chaincode_name = conf['misc']['chaincode_name']
#
#     print('Querying chaincode in the channel \'%(channel_name)s\' on the peer \'%(peer_host)s\' ...' % {
#         'channel_name': channel_name,
#         'peer_host': peer['host']
#     }, flush=True)
#
#     try:
#         output = check_output(['peer', 'chaincode', 'query',
#                                '-C', channel_name,
#                                '-n', chaincode_name,
#                                '-c', arg]).decode()
#     except CalledProcessError as e:
#         output = e.output.decode()
#         print('Error:', flush=True)
#         print(output, flush=True)
#         # clean env variables
#         clean_env_variables()
#     else:
#         try:
#             value = json.loads(output)
#         except:
#             value = output
#         else:
#             msg = 'Query of channel \'%(channel_name)s\' on peer \'%(peer_host)s\' was successful' % {
#                 'channel_name': channel_name,
#                 'peer_host': peer['host']
#             }
#             print(msg, flush=True)
#             print(value, flush=True)
#
#         finally:
#             # clean env variables
#             clean_env_variables()
#             return value



def queryChaincodeFromFirstPeer(org, fcn, args, chaincode_version=None):
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
        fcn=fcn,
        args=args,
        cc_name=chaincode_name,
        cc_version=chaincode_version
    ))

    return response

# def queryChaincodeFromFirstPeerFirstOrgAfterInvoke():
#     org_name = 'owkin'
#     org = [x for x in conf['orgs'] if x['name'] == org_name][0]
#     peer = org['peers'][0]
#
#     print('Try to query chaincode from first peer first org after invoke', flush=True)
#
#     starttime = int(time.time())
#     while int(time.time()) - starttime < 15:
#         call(['sleep', '1'])
#         data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
#                                   org,
#                                   peer)
#         # data should not be null
#         print(data, flush=True)
#         if isinstance(data, list) and len(data) == 2:
#             print('Correctly added and got', flush=True)
#             return True
#
#         print('.', end='', flush=True)
#
#     print('\n/!\ Failed to query chaincode after invoke', flush=True)
#     return False
#
#
# def queryChaincodeFromSecondPeerSecondOrg():
#     org_name = 'chu-nantes'
#     org = [x for x in conf['orgs'] if x['name'] == org_name][0]
#     peer = org['peers'][1]
#
#     print('Try to query chaincode from second peer second org', flush=True)
#
#     starttime = int(time.time())
#     while int(time.time()) - starttime < 15:
#         call(['sleep', '1'])
#         data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
#                                   org,
#                                   peer)
#         if isinstance(data, list) and len(data) == 2:
#             print('Correctly added and got', flush=True)
#             return True
#
#         print('.', end='', flush=True)
#
#     print('/!\ Failed to query chaincode with added value', flush=True)
#     return False


def invokeChainCode(fcn, args, org_name, peers):

    requestor = cli.get_user(org_name, 'admin')
    channel_name = 'substrachannel'
    chaincode_name = 'substracc'
    chaincode_version = '2.0'

    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(cli.chaincode_invoke(
        requestor=requestor,
        channel_name=channel_name,
        peers=peers,
        fcn=fcn,
        args=args,
        cc_name=chaincode_name,
        cc_version=chaincode_version,
        wait_for_event=True
    ))

    print(response)

    return json.loads(response)


def invokeChainCodeBinary(args, org, orderer, peer):

    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'
    channel_name = org['misc']['channel_name']
    chaincode_name = org['misc']['chaincode_name']

    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_user_msp_dir)

    print('Sending invoke transaction (with waitForEvent) to %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']},
          flush=True)

    tls_orderer_client_dir = os.path.join(orderer['tls']['dir']['external'], orderer['tls']['client']['dir'])
    tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])

    output = subprocess.run(['../../bin/peer',
                             'chaincode', 'invoke',
                             '-C', channel_name,
                             '-n', chaincode_name,
                             '-c', args,
                             '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']['external']},
                             '--tls',
                             '--clientauth',
                             '--cafile', os.path.join(tls_orderer_client_dir, orderer['tls']['client']['ca']),
                             '--certfile', os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                             '--keyfile', os.path.join(tls_peer_client_dir, peer['tls']['client']['key']),
                             '--waitForEvent'
                             ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    data = output.stderr.decode('utf-8')

    print(data, flush=True)

    # clean env variables
    clean_env_variables()

    try:
        # Format it to get generated key
        data = json.loads(data.split('result: status:')[1].split('\n')[0].split('payload:')[1].replace(' ', '').replace('"', '').replace('\\', '"'))
    except:
        return ''
    else:
        return data

def invokeChaincodeFirstPeers(orgs):

    # should fail
    # args = '{"Args":["registerDataset","liver slide"]}'
    # invokeChainCode(args, org, peer)

    # # create dataset with chu-nantes org
    # org_name = 'chu-nantes'
    # org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    # peer = org['peers'][0]

    org = [x for x in orgs if x['type'] == 'client' and x['name'] == 'owkin'][0]
    # orderer = [x for x in orgs if x['type'] == 'orderer'][0]['orderers'][0]
    # peer = org['peers'][0]
    #
    # args = '{"Args":["registerDataManager","ISIC 2018","ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994","http://chunantes.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener/","Images","7a90514f88c70002608a9868681dd1589ea598e78d00a8cd7783c3ea0f9ceb09","http://chunantes.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description/","","all"]}'
    # dataset = invokeChainCodeBinary(args, org, orderer, peer)

    res = queryChaincodeFromFirstPeer(org, 'queryObjectives', None, '2.0')
    print(res)

    fcn = 'registerDataManager'
    args=[
        'ISIC 2018',
        'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994',
        'http://chunantes.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener/',
        'Images',
        '7a90514f88c70002608a9868681dd1589ea598e78d00a8cd7783c3ea0f9ceb09',
        'http://chunantes.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description/',
        '',
        'all'
    ]
    dataset = invokeChainCode(fcn, args, 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    res = queryChaincodeFromFirstPeer(org, 'queryDataset', [dataset['key']], '2.0')
    print(res)


    # # register train data on dataset chu nantes (will take dataset creator as worker)
    # args = '{"Args":["registerData","62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9","%s","false"]}' % dataset_chunantes
    # invokeChainCode(args, org, peer)
    #
    # # register test data on dataset_chunantes
    # args = '{"Args":["registerData","61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b, 0e597cec32d7f5b147c78002b134062923782ccac0e9cbfdd06a0298e7949172", "%s","true"]}' % dataset_chunantes
    # invokeChainCode(args, org, peer)
    #
    # # create dataset, test data and challenge on owkin
    # #######
    # # /!\ #
    # #######
    #
    # org_name = 'owkin'
    # org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    # peer = org['peers'][0]
    #
    # #######
    # # /!\ #
    # #######
    #
    # # create second dataset with owkin center
    # args = '{"Args":["registerDataset","Simplified ISIC 2018","b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0","http://owkin.substrabac:8000/dataset/b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0/opener/","Images","258bef187a166b3fef5cb86e68c8f7e154c283a148cd5bc344fec7e698821ad3","http://owkin.substrabac:8000/dataset/b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0/description/","","all"]}'
    # dataset_owkin = invokeChainCode(args, org, peer)
    #
    # # register test data on dataset on owkin center (will take dataset creator as worker)
    # args = '{"Args":["registerData","e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1, 4b5152871b181d10ee774c10458c064c70710f4ba35938f10c0b7aa51f7dc010", "%s","true"]}' % dataset_owkin
    # invokeChainCode(args, org, peer)
    #
    # # register train data on dataset_owkin
    # args = '{"Args":["registerData","93e4b1e040b08cfa8a68b13f9dddb95a6672e8a377378545b2b1254691cfc060, eed4c6ea09babe7ca6428377fff6e54102ef5cdb0cae593732ddbe3f224217cb", "%s","true"]}' % dataset_owkin
    # invokeChainCode(args, org, peer)
    #
    # # register test data on dataset_owkin
    # args = '{"Args":["registerData","2d0f943aa81a9cb3fe84b162559ce6aff068ccb04e0cb284733b8f9d7e06517e, 533ee6e7b9d8b247e7e853b24547f57e6ef351852bac0418f13a0666173448f1", "%s","true"]}' % dataset_owkin
    # invokeChainCode(args, org, peer)
    #
    # args = '{"Args":["queryDatasets"]}'
    # chainCodeQueryWith(args, org, peer)
    #
    # # create challenge
    # args = '{"Args":["registerChallenge", "Simplified skin lesion classification", "6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c", "http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/description/", "macro-average recall", "0bc732c26bafdc41321c2bffd35b6835aa35f7371a4eb02994642c2c3a688f60", "http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/metrics/", "%s:2d0f943aa81a9cb3fe84b162559ce6aff068ccb04e0cb284733b8f9d7e06517e, 533ee6e7b9d8b247e7e853b24547f57e6ef351852bac0418f13a0666173448f1", "all"]}' % dataset_owkin
    # invokeChainCode(args, org, peer)
    #
    # # go back to chu-nantes
    # #######
    # # /!\ #
    # #######
    #
    # org_name = 'chu-nantes'
    # org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    # peer = org['peers'][0]
    #
    # #######
    # # /!\ #
    # #######
    #
    # # create challenge
    # args = '{"Args":["registerChallenge", "Skin Lesion Classification Challenge", "d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f", "http://chunantes.substrabac:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/description/", "macro-average recall", "750f622262854341bd44f55c1018949e9c119606ef5068bd7d137040a482a756", "http://chunantes.substrabac:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/metrics/", "%s:61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b", "all"]}' % dataset_chunantes
    # invokeChainCode(args, org, peer)
    #
    # # create algo
    # args = '{"Args":["registerAlgo","Logistic regression","9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a","http://chunantes.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/file/","124a0425b746d7072282d167b53cb6aab3a31bf1946dae89135c15b0126ebec3","http://chunantes.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/description/","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    # invokeChainCode(args, org, peer)
    #
    # # create second algo on challenge Simplified skin lesion classification
    # args = '{"Args":["registerAlgo","Logistic regression for balanced problem","7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0","http://chunantes.substrabac:8001/algo/7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0/file/","3b1281cbdd6ebfec650d0a9f932a64e45a27262848065d7cecf11fd7191b4b1f","http://chunantes.substrabac:8001/algo/7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0/description/","6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c","all"]}'
    # invokeChainCode(args, org, peer)
    #
    # # create third algo
    # args = '{"Args":["registerAlgo","Neural Network","0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f","http://chunantes.substrabac:8001/algo/0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f/file/","b9463411a01ea00869bdffce6e59a5c100a4e635c0a9386266cad3c77eb28e9e","http://chunantes.substrabac:8001/algo/0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f/description/","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    # invokeChainCode(args, org, peer)
    #
    # # create fourth algo
    # args = '{"Args":["registerAlgo","Random Forest","f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284","http://chunantes.substrabac:8001/algo/f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284/file/","4acea40c4b51996c88ef279c5c9aa41ab77b97d38c5ca167e978a98b2e402675","http://chunantes.substrabac:8001/algo/f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284/description/","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    # invokeChainCode(args, org, peer)
    #
    # # query data of the dataset in chu nantes
    # args = '{"Args":["queryDatasetData","%s"]}' % dataset_chunantes
    # chainCodeQueryWith(args, org, peer)
    #
    # args = '{"Args":["queryTraintuples"]}'
    # chainCodeQueryWith(args, org, peer)
    #
    # args = '{"Args":["createTraintuple","9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a","", "%s", "62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9", "", ""]}' % dataset_chunantes
    # traintuple = invokeChainCode(args, org, peer)
    #
    # # recreation of traintuple should fail
    # invokeChainCode(args, org, peer)
    #
    # args = '{"Args":["logStartTrain","%s"]}' % traintuple
    # invokeChainCode(args, org, peer)
    #
    # args = '{"Args":["queryTraintuples"]}'
    # chainCodeQueryWith(args, org, peer)
    #
    # args = '{"Args":["logSuccessTrain","' + traintuple + '","10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568, http://chunantes.substrabac:8001/model/10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568/file/","0.91","no error, ah ah ah"]}'
    # invokeChainCode(args, org, peer)
    #
    # # go back to owkin for creating testtuple
    # #######
    # # /!\ #
    # #######
    #
    # org_name = 'owkin'
    # org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    # peer = org['peers'][0]
    #
    # #######
    # # /!\ #
    # #######
    #
    # args = '{"Args":["createTesttuple","%s"]}' % traintuple
    # testtuple = invokeChainCode(args, org, peer)
    #
    # #######
    # # /!\ #
    # #######
    #
    # org_name = 'chu-nantes'
    # org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    # peer = org['peers'][0]
    #
    # #######
    # # /!\ #
    # #######
    #
    # # back to chu-nantes who own test data on this testtuple related dataset
    # args = '{"Args":["logStartTest","%s"]}' % testtuple
    # invokeChainCode(args, org, peer)
    #
    # args = '{"Args":["logSuccessTest","' + testtuple + '","0.99","still no error, suprah ah ah"]}'
    # invokeChainCode(args, org, peer)


def init_cli(orgs):
    for org in [x for x in orgs if x['type'] == 'orderer']:
        # add orderer organization
        cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

        # add orderer admin
        orderer_org_admin = org['users']['admin']
        orderer_org_admin_home = orderer_org_admin['home']
        orderer_org_admin_msp_dir = os.path.join(orderer_org_admin_home, 'msp')
        # register admin
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
            tls_orderer_client_dir = os.path.join(o['tls']['dir']['external'], o['tls']['client']['dir'])
            orderer = Orderer(o['name'],
                              endpoint=f"{o['host']}:{o['port']['internal']}",
                              tls_ca_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['ca']),
                              client_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['cert']),
                              client_key_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['key']),
                              )

            cli._orderers.update({o['name']: orderer})

        # add channel on cli if needed
        channel_name = org['misc']['channel_name']
        if not cli.get_channel(org['misc']['channel_name']):
            cli._channels.update({channel_name: cli.new_channel(channel_name)})

    for org in [x for x in orgs if x['type'] == 'client']:

        # add orderer organization
        cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

        org_admin = org['users']['admin']
        org_admin_home = org['users']['admin']['home']
        org_admin_msp_dir = os.path.join(org_admin_home, 'msp')
        # register admin
        admin_cert_path = os.path.join(org_admin_msp_dir, 'signcerts', 'cert.pem')
        admin_key_path = os.path.join(org_admin_msp_dir, 'keystore', 'key.pem')
        admin = create_user(name=org_admin['name'],
                                org=org['name'],
                                state_store=cli.state_store,
                                msp_id=org['mspid'],
                                cert_path=admin_cert_path,
                                key_path=admin_key_path)
        cli._organizations[org['name']]._users.update({org_admin['name']: admin})

        # register peers
        for peer in org['peers']:
            tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])

            # add peer in cli

            ##########################################################################################
            # For debugging, you can use peer['port']['external'] instead of peer['port']['internal']
            ##########################################################################################

            p = Peer(endpoint=f"{peer['host']}:{peer['port']['internal']}",
                     tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                     client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                     client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
            cli._peers.update({peer['name']: p})

        # add channel on cli if needed
        channel_name = org['misc']['channel_name']
        if not cli.get_channel(org['misc']['channel_name']):
            cli._channels.update({channel_name: cli.new_channel(channel_name)})


def run(orgs):
    res = True

    # Invoke chaincode with 1st peers of each org
    invokeChaincodeFirstPeers(orgs)

    # # Query chaincode from the 1st peer of the 1st org after Invoke
    # res = res and queryChaincodeFromFirstPeerFirstOrgAfterInvoke()
    #
    # # Query chaincode on 2nd peer of 2nd org
    # res = res and queryChaincodeFromSecondPeerSecondOrg()
    #
    if res:
        print('Congratulations! The fixtures have been loaded successfully.', flush=True)
        call(['touch', '/substra/data/log/fixtures.successful'])
    else:
        print('Loading fixtures failed.', flush=True)
        call(['touch','/substra/data/log/fixtures.fail'])


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    init_cli(orgs)

    run(orgs)

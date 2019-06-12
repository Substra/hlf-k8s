import asyncio
import glob
import json
import os

from subprocess import call

from hfc.fabric import Client
from hfc.fabric.orderer import Orderer
from hfc.fabric.organization import create_org
from hfc.fabric.peer import Peer
from hfc.fabric.user import create_user
from hfc.util.keyvaluestore import FileKeyValueStore

cli = Client()
cli._state_store = FileKeyValueStore('/tmp/kvs/')

SUBSTRA_PATH = '/substra'


def queryChaincode(fcn, args, org_name, peers):
    print(f"Query chaincode on org {org_name}", flush=True)

    requestor = cli.get_user(org_name, 'admin')
    channel_name = 'substrachannel'
    chaincode_name = 'substracc'
    chaincode_version = '2.0'

    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(cli.chaincode_query(
        requestor=requestor,
        channel_name=channel_name,
        peers=peers,
        fcn=fcn,
        args=args,
        cc_name=chaincode_name,
        cc_version=chaincode_version
    ))

    return response


def invokeChainCode(fcn, args, org_name, peers):
    print(f"Invoke chaincode on org {org_name}", flush=True)

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

    try:
        res = json.loads(response)
    except:
        res = response
    finally:
        return res

def invokeChaincodeFirstPeers():
    res = queryChaincode('queryObjectives', None, 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    fcn = 'registerDataManager'
    args = {
        'name': 'ISIC 2018',
        'openerHash': 'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994',
        'openerStorageAddress':'http://chunantes.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener/',
        'type': 'Images',
        'descriptionHash': '7a90514f88c70002608a9868681dd1589ea598e78d00a8cd7783c3ea0f9ceb09',
        'descriptionStorageAddress': 'http://chunantes.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description/',
        'objectiveKey': '',
        'permissions': 'all'
    }
    datamanager_chunantes = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    if 'key' in datamanager_chunantes:
        datamanager_chunantes_key = datamanager_chunantes['key']
    # debug purposes
    else:
        datamanager_chunantes_key = 'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994'

    res = queryChaincode('queryDataset', [json.dumps({'key': datamanager_chunantes_key})], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    print(res)


    # register train data on dataset chu nantes (will take dataset creator as worker)
    fcn = 'registerDataSample'
    args = {
        'hashes': '62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9',
        'dataManagerKeys': datamanager_chunantes_key,
        'testOnly': json.dumps(False)
    }
    data_samples = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    if 'keys' in data_samples:
        data_chunantes_train_keys_1 = data_samples['keys']
    # debug purpose only
    else:
        data_chunantes_train_keys_1 = ["62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a",
                                  "42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9"]


    # register test data on datamanager_chunantes
    args = {
        'hashes': '61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b, 0e597cec32d7f5b147c78002b134062923782ccac0e9cbfdd06a0298e7949172',
        'dataManagerKeys': datamanager_chunantes_key,
        'testOnly': json.dumps(True)
    }
    data_keys = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    if 'keys' in data_keys:
        data_chunantes_test_keys_1 = data_keys['keys']
    # debug purpose only
    else:
        data_chunantes_test_keys_1 = ["61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b",
                     "0e597cec32d7f5b147c78002b134062923782ccac0e9cbfdd06a0298e7949172"]

    # create datamanager, test data and challenge on owkin
    # #######
    # # /!\ #
    # #######
    # org_name = 'owkin'
    # #######
    # # /!\ #
    # #######

    # create second dataset with owkin center
    fcn = 'registerDataManager'
    args = {
        'name': 'Simplified ISIC 2018',
        'openerHash': 'b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0',
        'openerStorageAddress': 'http://owkin.substrabac:8000/dataset/b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0/opener/',
        'type': 'Images',
        'descriptionHash': '258bef187a166b3fef5cb86e68c8f7e154c283a148cd5bc344fec7e698821ad3',
        'descriptionStorageAddress': 'http://owkin.substrabac:8000/dataset/b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0/description/',
        'objectiveKey': '',
        'permissions': 'all'
    }
    datamanager_owkin = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    if 'key' in datamanager_owkin:
        datamanager_owkin_key = datamanager_owkin['key']
    # debug purposes
    else:
        datamanager_owkin_key = 'b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0'

    # register test data on dataset on owkin center (will take dataset creator as worker)
    fcn = 'registerDataSample'
    args = {
        'hashes': 'e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1, 4b5152871b181d10ee774c10458c064c70710f4ba35938f10c0b7aa51f7dc010',
        'dataManagerKeys': datamanager_owkin_key,
        'testOnly': json.dumps(True)
    }
    data_keys = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    # register train data on datamanager_owkin
    args = {
        'hashes': '93e4b1e040b08cfa8a68b13f9dddb95a6672e8a377378545b2b1254691cfc060, eed4c6ea09babe7ca6428377fff6e54102ef5cdb0cae593732ddbe3f224217cb',
        'dataManagerKeys': datamanager_owkin_key,
        'testOnly': json.dumps(False)
    }
    data_keys = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    # register test data on datamanager_owkin
    args = {
        'hashes': '2d0f943aa81a9cb3fe84b162559ce6aff068ccb04e0cb284733b8f9d7e06517e, 533ee6e7b9d8b247e7e853b24547f57e6ef351852bac0418f13a0666173448f1',
        'dataManagerKeys': datamanager_owkin_key,
        'testOnly': json.dumps(True)
    }
    data_keys = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    res = queryChaincode('queryDataManagers', [], 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    # create objective
    fcn = 'registerObjective'
    args = {
        'name': 'Simplified skin lesion classification',
        'descriptionHash': '6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c',
        'descriptionStorageAddress': 'http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/description/',
        'metricsName': 'macro-average recall',
        'metricsHash': '0bc732c26bafdc41321c2bffd35b6835aa35f7371a4eb02994642c2c3a688f60',
        'metricsStorageAddress': 'http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/metrics/',
        'testDataset': f'{datamanager_owkin_key}:2d0f943aa81a9cb3fe84b162559ce6aff068ccb04e0cb284733b8f9d7e06517e, 533ee6e7b9d8b247e7e853b24547f57e6ef351852bac0418f13a0666173448f1',
        'permissions': 'all'
    }
    objective_owkin = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    # # go back to chu-nantes
    # #######
    # # /!\ #
    # #######
    # org_name = 'chu-nantes'
    # #######
    # # /!\ #
    # #######

    # create objective
    fcn = 'registerObjective'
    args = {
        'name': 'Skin Lesion Classification Challenge',
        'descriptionHash': 'd5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f',
        'descriptionStorageAddress': 'http://chunantes.substrabac:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/description/',
        'metricsName': 'macro-average recall',
        'metricsHash': '750f622262854341bd44f55c1018949e9c119606ef5068bd7d137040a482a756',
        'metricsStorageAddress': 'http://chunantes.substrabac:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/metrics/',
        'testDataset': f'{datamanager_chunantes_key}:61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b',
        'permissions': 'all'
    }
    objective_chunantes = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    if 'key' in objective_chunantes:
        objective_chunantes_key = objective_chunantes['key']
    # debugging purposes
    else:
        objective_chunantes_key = 'd5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f'

    # create algo
    fcn = 'registerAlgo'
    args = {
        'name': 'Logistic regression',
        'hash': '9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a',
        'storageAddress': 'http://chunantes.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/file/',
        'descriptionHash': '124a0425b746d7072282d167b53cb6aab3a31bf1946dae89135c15b0126ebec3',
        'descriptionStorageAddress': 'http://chunantes.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/description/',
        'permissions': 'all'
    }
    algo_chunantes_1 = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    if 'key' in algo_chunantes_1:
        algo_chunantes_1_key = algo_chunantes_1['key']
    # debugging purposes
    else:
        algo_chunantes_1_key = '9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a'

    # create second algo on challenge Simplified skin lesion classification
    args = {
        'name': 'Logistic regression for balanced problem',
        'hash': '7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0',
        'storageAddress': 'http://chunantes.substrabac:8001/algo/7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0/file/',
        'descriptionHash': '3b1281cbdd6ebfec650d0a9f932a64e45a27262848065d7cecf11fd7191b4b1f',
        'descriptionStorageAddress': 'http://chunantes.substrabac:8001/algo/7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0/description/',
        'permissions': 'all'
    }
    algo_chunantes_2 = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    # create third algo
    args = {
        'name': 'Neural Network',
        'hash': '0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f',
        'storageAddress': 'http://chunantes.substrabac:8001/algo/0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f/file/',
        'descriptionHash': 'b9463411a01ea00869bdffce6e59a5c100a4e635c0a9386266cad3c77eb28e9e',
        'descriptionStorageAddress': 'http://chunantes.substrabac:8001/algo/0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f/description/',
        'permissions': 'all'
    }
    algo_chunantes_3 = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    # create fourth algo
    args = {
        'name': 'Random Forest',
        'hash': 'f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284',
        'storageAddress': 'http://chunantes.substrabac:8001/algo/f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284/file/',
        'descriptionHash': '4acea40c4b51996c88ef279c5c9aa41ab77b97d38c5ca167e978a98b2e402675',
        'descriptionStorageAddress': 'http://chunantes.substrabac:8001/algo/f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284/description/',
        'permissions': 'all'
    }
    algo_chunantes_4 = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    # query data of the dataset in chu nantes
    res = queryChaincode('queryDataManagers', [], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    print(res)

    res = queryChaincode('queryTraintuples', [], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    print(res)

    fcn = 'createTraintuple'
    args = {
        'algoKey': algo_chunantes_1_key,
        'objectiveKey': objective_chunantes_key,
        'inModels': '',
        'dataManagerKey': datamanager_chunantes_key,
        'dataSampleKeys': ','.join([x for x in data_chunantes_train_keys_1]),
        'flTask': '',
        'rank': '',
        'tag': 'foo'
    }
    traintuple = invokeChainCode(fcn, [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    #recreation of traintuple should fail
    if isinstance(traintuple, dict) and 'key' in traintuple:
        traintuple_key = traintuple['key']
    # debug purposes
    else:
        traintuple_key = traintuple.split('tkey: ')[1][0:-1]

    args = {
        'key': traintuple_key
    }
    invokeChainCode('logStartTrain', [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    res = queryChaincode('queryTraintuples', [], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    print(res)

    args = {
        'key': traintuple_key,
        'log': 'ok',
        'outModel': {
            'hash': '10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568',
            'storageAddress': 'http://chunantes.substrabac:8001/model/10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568/file/',
        },
        'perf': 0.91,
    }
    invokeChainCode('logSuccessTrain', [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])
    # # go back to owkin for creating testtuple
    # #######
    # # /!\ #
    # #######
    # org_name = 'owkin'
    # #######
    # # /!\ #
    # #######

    fcn = 'createTesttuple'
    args = {
        'traintupleKey': traintuple_key,
        'dataManagerKey': datamanager_chunantes_key,
        'dataSampleKeys': ','.join(data_chunantes_test_keys_1),
        'tag': 'foo'
    }
    testtuple = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    # #######
    # # /!\ #
    # #######
    # org_name = 'chu-nantes'
    # #######
    # # /!\ #
    # #######

    if isinstance(testtuple, dict) and 'key' in testtuple:
        testtuple_key = testtuple['key']
    # debug purposes
    else:
        testtuple_key = traintuple.split('tkey: ')[1][0:-1]

    args = {
        'key': testtuple_key,
    }
    invokeChainCode('logStartTest', [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])

    args = {
        'key': testtuple_key,
        'log': 'ok',
        'perf': 0.99,
    }
    invokeChainCode('logSuccessTest', [json.dumps(args)], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])


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

            p = Peer(endpoint=f"{peer['host']}:{peer['port']['external']}",
                     tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                     client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                     client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
            cli._peers.update({peer['name']: p})

        # add channel on cli if needed
        channel_name = org['misc']['channel_name']
        if not cli.get_channel(org['misc']['channel_name']):
            cli._channels.update({channel_name: cli.new_channel(channel_name)})


def run():
    res = True

    # Invoke chaincode with 1st peers of each org
    invokeChaincodeFirstPeers()

    # Query chaincode from the 1st peer of the 1st org after Invoke
    res = res and queryChaincode('queryObjectives', [], 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    # Query chaincode on 2nd peer of 2nd org
    res = res and queryChaincode('queryObjectives', [], 'chu-nantes', [cli.get_peer('peer2-chu-nantes')])
    print(res)

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

    run()

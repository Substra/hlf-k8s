import asyncio
import glob
import json
import os

from subprocess import call

from fixtures.utils import init_cli

SUBSTRA_PATH = '/substra'


def queryChaincode(fcn, args, org_name, peers):
    print(f"Query chaincode on org {org_name}", flush=True)

    requestor = cli.get_user(org_name, 'admin')
    channel_name = 'substrachannel'
    chaincode_name = 'substracc'

    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(cli.chaincode_query(
        requestor=requestor,
        channel_name=channel_name,
        peers=peers,
        fcn=fcn,
        args=args,
        cc_name=chaincode_name,
    ))

    return response


def invokeChainCode(fcn, args, org_name, peers):
    print(f"Invoke chaincode on org {org_name}", flush=True)

    requestor = cli.get_user(org_name, 'admin')
    channel_name = 'substrachannel'
    chaincode_name = 'substracc'

    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(cli.chaincode_invoke(
        requestor=requestor,
        channel_name=channel_name,
        peers=peers,
        fcn=fcn,
        args=args,
        cc_name=chaincode_name,
        wait_for_event=True
    ))

    try:
        res = json.loads(response)
    except:
        res = response
    finally:
        print(res)
        return res


def setup():

    res = queryChaincode('queryObjectives', None, 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    fcn = 'registerDataManager'
    args = {
        'name': 'ISIC 2018',
        'openerHash': 'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994',
        'openerStorageAddress': 'http://owkin.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener/',
        'type': 'Images',
        'descriptionHash': '7a90514f88c70002608a9868681dd1589ea598e78d00a8cd7783c3ea0f9ceb09',
        'descriptionStorageAddress': 'http://owkin.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description/',
        'objectiveKey': '',
        'permissions': 'all'
    }
    datamanager_owkin = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    if 'key' in datamanager_owkin:
        datamanager_owkin_key = datamanager_owkin['key']
    # debug purposes
    else:
        datamanager_owkin_key = 'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994'

    res = queryChaincode('queryDataset', [json.dumps({'key': datamanager_owkin_key})], 'owkin',
                         [cli.get_peer('peer1-owkin')])
    print(res)

    # register train data on dataset chu nantes (will take dataset creator as worker)
    fcn = 'registerDataSample'
    args = {
        'hashes': '62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9',
        'dataManagerKeys': datamanager_owkin_key,
        'testOnly': json.dumps(False)
    }
    data_samples = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    if 'keys' in data_samples:
        data_owkin_train_keys_1 = data_samples['keys']
    # debug purpose only
    else:
        data_owkin_train_keys_1 = ["62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a",
                                       "42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9"]


    # register train data on dataset chu nantes (will take dataset creator as worker)
    fcn = 'registerDataSample'
    args = {
        'hashes': '61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b, 0e597cec32d7f5b147c78002b134062923782ccac0e9cbfdd06a0298e7949172',
        'dataManagerKeys': datamanager_owkin_key,
        'testOnly': json.dumps(True)
    }
    data_samples = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    if 'keys' in data_samples:
        data_owkin_test_keys_1 = data_samples['keys']
    # debug purpose only
    else:
        data_owkin_test_keys_1 = ["61b113ac7142bdd1cc8a824cd29940ce0e22e2381b25e0efe34f64cad5a5ff9b",
                                       "0e597cec32d7f5b147c78002b134062923782ccac0e9cbfdd06a0298e7949172"]

    # create objective
    fcn = 'registerObjective'
    args = {
        'name': 'Simplified skin lesion classification',
        'descriptionHash': '6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c',
        'descriptionStorageAddress': 'http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/description/',
        'metricsName': 'macro-average recall',
        'metricsHash': '0bc732c26bafdc41321c2bffd35b6835aa35f7371a4eb02994642c2c3a688f60',
        'metricsStorageAddress': 'http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/metrics/',
        'testDataset': f'{datamanager_owkin_key}:{", ".join(data_owkin_test_keys_1)}',
        'permissions': 'all'
    }
    objective_owkin = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])
    if 'key' in objective_owkin:
        objective_owkin_key = objective_owkin['key']
    # debugging purposes
    else:
        objective_owkin_key = '6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c'

    # create algo
    fcn = 'registerAlgo'
    args = {
        'name': 'Logistic regression',
        'hash': '9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a',
        'storageAddress': 'http://owkin.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/file/',
        'descriptionHash': '124a0425b746d7072282d167b53cb6aab3a31bf1946dae89135c15b0126ebec3',
        'descriptionStorageAddress': 'http://owkin.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/description/',
        'permissions': 'all'
    }
    algo_owkin_1 = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])
    if 'key' in algo_owkin_1:
        algo_owkin_1_key = algo_owkin_1['key']
    # debugging purposes
    else:
        algo_owkin_1_key = '9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a'

    # query data of the dataset in chu nantes
    res = queryChaincode('queryDataManagers', [], 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    res = queryChaincode('queryTraintuples', [], 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    # create parent traintuple
    fcn = 'createTraintuple'
    print(objective_owkin_key, flush=True)
    print(datamanager_owkin_key, flush=True)
    print(','.join([x for x in data_owkin_train_keys_1]), flush=True)
    args = {
        'algoKey': algo_owkin_1_key,
        'objectiveKey': objective_owkin_key,
        'inModels': '',
        'dataManagerKey': datamanager_owkin_key,
        'dataSampleKeys': ','.join(data_owkin_train_keys_1),
        'flTask': '',
        'rank': '',
        'tag': 'foo'
    }
    traintuple = invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])

    if isinstance(traintuple, dict) and 'key' in traintuple:
        traintuple_key = traintuple['key']
    # debug purposes
    else:
        traintuple_key = traintuple.split('tkey: ')[1][0:-1]

    print(traintuple_key)


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    cli = init_cli(orgs)

    setup()

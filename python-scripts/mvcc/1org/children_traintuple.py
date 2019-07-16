import asyncio
import glob
import hashlib
import json
import os
import uuid


from utils.cli import init_cli

SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')


def queryChaincode(fcn, args, org_name, peers):
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
        if res == 'MVCC_READ_CONFLICT':
            print(res)
        return res


def register_random_algo():
    fcn = 'registerAlgo'
    u = uuid.uuid4()
    hash = hashlib.sha256(u.bytes).hexdigest()
    descriptionHash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    args = {
        'name': str(u),
        'hash': hash,
        'storageAddress': f'http://owkin.substrabac:8001/algo/{hash}/file/',
        'descriptionHash': descriptionHash,
        'descriptionStorageAddress': f'http://owkin.substrabac:8001/algo/{hash}/description/',
        'permissions': 'all'
    }
    invokeChainCode(fcn, [json.dumps(args)], 'owkin', [cli.get_peer('peer1-owkin')])
    return hash


def run():
    res = json.loads(queryChaincode('queryTraintuples', [], 'owkin', [cli.get_peer('peer1-owkin')]))
    traintuple_key = res[len(res) - 1]['key']  # get oldest
    objective_owkin_key = '6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c'
    datamanager_owkin_key = 'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994'
    data_owkin_train_keys_1 = '62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9'

    # create different children traintuples
    for i in range(0, 20):
        fcn = 'createTraintuple'
        args = [json.dumps({
                 'algoKey': register_random_algo(),
                 'objectiveKey': objective_owkin_key,
                 'inModels': traintuple_key,
                 'dataManagerKey': datamanager_owkin_key,
                 'dataSampleKeys': data_owkin_train_keys_1,
                 'flTask': '',
                 'rank': '',
                 'tag': str(i)
             })]
        invokeChainCode(fcn, args, 'owkin', [cli.get_peer('peer1-owkin')])


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    cli = init_cli(orgs)

    # add channel on cli
    channel_name = orgs[0]['misc']['channel_name']
    cli.new_channel(channel_name)

    run()

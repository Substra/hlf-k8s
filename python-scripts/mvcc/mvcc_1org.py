import asyncio
import glob
import json
import os
from multiprocessing import Pool

from subprocess import call

from utils.cli import init_cli

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

    print(response)

    try:
        res = json.loads(response)
    except:
        res = response
    finally:
        print('res: ', res, flush=True)
        return res


def createInParallel(fcn, args, org_name, peers):
    invokeChainCode(fcn, args, org_name, peers)


def setup():
    res = queryChaincode('queryObjectives', None, 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    print('register DataManager', flush=True)
    fcn = 'registerDataManager'
    with Pool(processes=20) as pool:
        pool.starmap(createInParallel, [
            (fcn,
             [json.dumps({
                 'name': 'ISIC 2018',
                 'openerHash': 'ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994',
                 'openerStorageAddress': 'http://owkin.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener/',
                 'type': 'Images',
                 'descriptionHash': '7a90514f88c70002608a9868681dd1589ea598e78d00a8cd7783c3ea0f9ceb09',
                 'descriptionStorageAddress': 'http://owkin.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description/',
                 'objectiveKey': '',
                 'permissions': 'all'
             })],
             'owkin',
             ['peer1-owkin']
             ) for i in range(0, 100)])


def run():
    res = True

    # Invoke chaincode with 1st peers of each org
    setup()

    # Query chaincode from the 1st peer of the 1st org after Invoke
    res = res and queryChaincode('queryObjectives', [], 'owkin', [cli.get_peer('peer1-owkin')])
    print(res)

    # Query chaincode on 2nd peer of 2nd org
    res = res and queryChaincode('queryObjectives', [], 'owkin', [cli.get_peer('peer2-owkin')])
    print(res)

    if res:
        print('Congratulations! The fixtures have been loaded successfully.', flush=True)
        call(['touch', '/substra/data/log/fixtures.successful'])
    else:
        print('Loading fixtures failed.', flush=True)
        call(['touch', '/substra/data/log/fixtures.fail'])


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    cli = init_cli(orgs)

    # add channel on cli
    channel_name = orgs[0]['misc']['channel_name']
    cli.new_channel(channel_name)

    run()

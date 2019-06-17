import asyncio
import glob
import json
import os
import time


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


def run():
    res = json.loads(queryChaincode('queryTraintuples', [], 'owkin', [cli.get_peer('peer1-owkin')]))
    traintuple_key = res[len(res) - 1]['key']  # get oldest
    print(traintuple_key)
    time.sleep(0.5)
    args = [json.dumps({'key': traintuple_key})]
    print(f'logStartTrain traintuple with key {traintuple_key}', flush=True)
    invokeChainCode('logStartTrain', args, 'owkin', [cli.get_peer('peer1-owkin')])


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    cli = init_cli(orgs)

    run()

# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import glob
import json
import os
import time


from utils.cli import init_cli

SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')


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

    res = json.loads(queryChaincode('queryTraintuples', [], 'chu-nantes', [cli.get_peer('peer1-chu-nantes')]))
    traintuple_key = res[len(res) - 1]['key']  # get oldest
    time.sleep(0.5)
    args = [json.dumps({'key': traintuple_key})]
    print(f'logStartTrain traintuple with key {traintuple_key}', flush=True)
    invokeChainCode('logStartTrain', args, 'chu-nantes', [cli.get_peer('peer1-chu-nantes')])


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    cli = init_cli(orgs)

    # add channel on cli
    channel_name = orgs[0]['misc']['channel_name']
    cli.new_channel(channel_name)

    run()

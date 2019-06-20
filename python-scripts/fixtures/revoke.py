
import pprint
import json
import glob
import os
import asyncio
import base64
import copy

from subprocess import call
from utils.cli import init_cli
from hfc.fabric import Client
from hfc.fabric_ca.caservice import ca_service
from hfc.fabric.block_decoder import decode_config

SUBSTRA_PATH = '/substra'
pp = pprint.PrettyPrinter(indent=2)


def run(cli, org, orderer):
    cacli = ca_service(target=f"https://{org['ca']['host']}:{org['ca']['port']['external']}",
                       ca_certs_path=org['ca']['certfile']['external'],
                       ca_name=org['ca']['name'])

    enrolledAdmin = cacli.enroll(org['users']['admin']['name'],
                                 org['users']['admin']['pass'])

    revoked_certs, crl = enrolledAdmin.revoke(
        org['users']['user']['name'], gencrl=True)

    pp.pprint(revoked_certs)
    pp.pprint(crl)

    requestor = cli.get_user(org['name'], org['users']['user']['name'])
    peers = [x['name'] for x in org['peers']]

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(cli.get_channel_config(
        requestor=requestor,
        channel_name=org['misc']['channel_name'],
        peers=peers
    ))

    config_envelope = results[0]

    old_config = decode_config(config_envelope.config)
    new_config = copy.deepcopy(old_config)
    new_config['channel_group']['groups']['Application']['groups'][org['name']
                                                                   ]['values']['MSP']['value']['config']['revocation_list'] = [crl]

    json.dump(old_config, open('old_config.json', 'w', encoding='utf8'))
    call(['configtxlator',
          'proto_encode',
          '--type', 'common.Config',
          '--input', 'old_config.json',
          '--output', 'old_config.block'
          ])

    json.dump(new_config, open('new_config.json', 'w', encoding='utf8'))
    call(['configtxlator',
          'proto_encode',
          '--type', 'common.Config',
          '--input', 'new_config.json',
          '--output', 'new_config.block'
          ])

    # Compute update
    call(['configtxlator',
          'compute_update',
          '--channel_id', org['misc']['channel_name'],
          '--original', 'old_config.block',
          '--updated', 'new_config.block',
          '--output', 'compute_update.pb'
          ])

    call(['configtxlator',
          'proto_decode',
          '--type', 'common.ConfigUpdate',
          '--input', 'compute_update.pb',
          '--output', 'config_update.json'
          ])

    # call(f"configtxlator compute_update --channel_id {org['misc']['channel_name']}"
    #      " --original old_config.block"
    #      " --updated new_config.block"
    #      " | "
    #      "configtxlator proto_decode --type common.ConfigUpdate"
    #      " --output config_update.json", shell=True)

    config_update = json.load(open('config_update.json'))

    config_update_as_envelope = {
        'payload': {
            'header': {
                'channel_header': {
                    'channel_id': org['misc']['channel_name'],
                    'type': 2,
                }
            },
            'data': {
                'config_update': config_update
            }
        }
    }

    json.dump(config_update_as_envelope, open(
        'proposal.json', 'w', encoding='utf-8'))

    config_tx_file = 'proposal.pb'

    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', config_tx_file])

    print('orderer name', orderer['orderers'][0]['name'])
    print('channel name', org['misc']['channel_name'])
    print('conf orderer', orderer['name'])
    print('admin orderer name', orderer['users']['admin']['name'])
    print('channel', cli.get_channel(org['misc']['channel_name']))

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(cli.channel_update(
        cli.get_orderer(orderer['orderers'][0]['name']),
        org['misc']['channel_name'],
        cli.get_user(org['name'], org['users']['admin']['name']),
        config_tx=config_tx_file))

    if res is False:
        raise Exception('Fail to update channel')

    response = loop.run_until_complete(cli.chaincode_query(
        requestor=requestor,
        channel_name=org['misc']['channel_name'],
        peers=peers,
        fcn='queryObjectives',
        args=None,
        cc_name=org['misc']['chaincode_name'],
    ))

    pp.pprint(response)


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]
    cli = init_cli(orgs)

    org_name = 'owkin'
    org = [x for x in orgs if x['name'] == org_name][0]
    orderer = [x for x in orgs if x['type'] == 'orderer'][0]

    cli.new_channel(org['misc']['channel_name'])

    run(cli, org, orderer)

import pprint
import json
import glob
import os
import asyncio
import copy
import time

from subprocess import call


from utils.cli import init_cli
from hfc.fabric_ca.caservice import ca_service
from hfc.fabric.block_decoder import decode_config

SUBSTRA_PATH = '/substra'
pp = pprint.PrettyPrinter(indent=2)


def revokeFabricUserAndGenerateCRL():

    username = org['users']['user']['name']
    port = org['ca']['port'][os.environ.get('ENV', 'external')]
    ca_certs_path = org['ca']['certfile']['external']
    cacli = ca_service(target=f"https://{org['ca']['host']}:{port}",
                       ca_certs_path=ca_certs_path,
                       ca_name=org['ca']['name'])

    enrolledAdmin = cacli.enroll(org['users']['admin']['name'],
                                 org['users']['admin']['pass'])

    revoked_certs, crl = enrolledAdmin.revoke(username, gencrl=True)

    return crl


def fetchConfigBlock():
    org_admin = cli.get_user(org['name'], org['users']['admin']['name'])
    peers = [x['name'] for x in org['peers']]

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(cli.get_channel_config(
        requestor=org_admin,
        channel_name=org['misc']['channel_name'],
        peers=peers
    ))
    config_envelope = results[0]
    return config_envelope


def createConfigUpdatePayloadWithCRL(old_config, crl):

    new_config = copy.deepcopy(old_config)
    new_config['channel_group']['groups']['Application']['groups'][org['name']]['values']['MSP']['value']['config'][
        'revocation_list'] = [crl]

    json.dump(old_config, open('/tmp/old_config.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--type', 'common.Config',
          '--input', '/tmp/old_config.json',
          '--output', '/tmp/old_config.block'
          ])

    json.dump(new_config, open('/tmp/new_config.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--type', 'common.Config',
          '--input', '/tmp/new_config.json',
          '--output', '/tmp/new_config.block'
          ])

    # Compute update
    call(['configtxlator',
          'compute_update',
          '--channel_id', org['misc']['channel_name'],
          '--original', '/tmp/old_config.block',
          '--updated', '/tmp/new_config.block',
          '--output', '/tmp/compute_update.pb'
          ])

    call(['configtxlator',
          'proto_decode',
          '--type', 'common.ConfigUpdate',
          '--input', '/tmp/compute_update.pb',
          '--output', '/tmp/config_update.json'
          ])

    config_update = json.load(open('/tmp/config_update.json'))

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

    json.dump(config_update_as_envelope, open('/tmp/proposal.json', 'w'))

    config_tx_file = '/tmp/proposal.pb'

    call(['configtxlator',
          'proto_encode',
          '--input', '/tmp/proposal.json',
          '--type', 'common.Envelope',
          '--output', config_tx_file])

    return config_tx_file


def updateConfigBlock(config_tx_file):
    org_admin = cli.get_user(org['name'], org['users']['admin']['name'])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli.channel_update(
        cli.get_orderer(orderer['orderers'][0]['name']),
        org['misc']['channel_name'],
        org_admin,
        config_tx=config_tx_file))

def queryAsRevokedUser():
    org_user = cli.get_user(org['name'], org['users']['user']['name'])
    peers = [x['name'] for x in org['peers']]

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(cli.chaincode_query(
            requestor=org_user,
            channel_name=org['misc']['channel_name'],
            peers=peers,
            fcn='queryObjectives',
            args=None,
            cc_name=org['misc']['chaincode_name'],
        ))
    except Exception as e:
        return 'access denied' in e.details()
    else:
        return False


def revokeFirstOrgUser():
    crl = revokeFabricUserAndGenerateCRL()

    config_envelope = fetchConfigBlock()

    old_config = decode_config(config_envelope.config)

    config_tx_file = createConfigUpdatePayloadWithCRL(old_config, crl)

    updateConfigBlock(config_tx_file)

    # wait for block being fetched by endorsing peer
    # TODO wait for channel_update waitForEvent in fabric-sdk-py
    time.sleep(2)

    if queryAsRevokedUser():
        print('Revokation Success')
        call(['touch', '/substra/data/log/revoke.successful'])
    else:
        print('Revokation Fail')
        call(['touch', '/substra/data/log/revoke.fail'])


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]
    cli = init_cli(orgs)

    org_name = 'owkin'
    org = [x for x in orgs if x['name'] == org_name][0]
    orderer = [x for x in orgs if x['type'] == 'orderer'][0]

    cli.new_channel(org['misc']['channel_name'])

    revokeFirstOrgUser()

import base64
import pprint
import json
import glob
import os
import asyncio
import copy
import time

from subprocess import call, CalledProcessError, check_output, STDOUT, Popen

import requests

from utils.cli import init_cli
from hfc.fabric_ca.caservice import ca_service
from hfc.fabric.block_decoder import decode_config

SUBSTRA_PATH = '/substra'
pp = pprint.PrettyPrinter(indent=2)

def set_env_variables(fabric_cfg_path, msp_dir):
    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir


def clean_env_variables():
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def revokeFabricUserAndGenerateCRL(org, username):
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    print(
        'Revoking the user \'%(username)s\' of the organization \'%(org_name)s\' with Fabric CA Client home directory set to %(org_admin_home)s and generating CRL ...' % {
            'username': username,
            'org_name': org['name'],
            'org_admin_home': org_admin_home
        }, flush=True)

    call(['fabric-ca-client',
          'revoke', '-d',
          '--url', 'https://rca-owkin:7054',
          '--tls.certfiles', '/substra/data/orgs/owkin/ca-cert.pem',
          '--caname', 'rca-owkin',
          '-M', org_admin_msp_dir,  # override msp dir for not taking one from bootstrap admin, but from admin
          '--revoke.name', username,
          '--gencrl'])

    with open(org_admin_msp_dir + '/crls/crl.pem', 'rb') as f:
        crl = base64.b64encode(f.read()).decode('utf8')

    return crl


def fetchConfigBlock(org, peer, orderer):
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'
    channel_name = org['misc']['channel_name']
    config_block_file = org['misc']['config_block_file']
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])

    print('Fetching the configuration block of the channel \'%s\'' % channel_name, flush=True)

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir)

    tls_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_orderer_client_dir = orderer['orderers'][0]['tls']['dir']['external'] + '/' + orderer['orderers'][0]['tls']['client']['dir']
    call(['peer', 'channel', 'fetch', 'config', config_block_file,
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['orderers'][0]['host'], 'port': orderer['orderers'][0]['port']['external']},
          '--tls',
          '--clientauth',
          '--cafile', os.path.join(tls_orderer_client_dir, orderer['orderers'][0]['tls']['client']['ca']),
          '--certfile', tls_client_dir + '/' + peer['tls']['client']['cert'],
          '--keyfile', tls_client_dir + '/' + peer['tls']['client']['key']
          ])

    # clean env variables
    clean_env_variables()


def createConfigUpdatePayloadWithCRL(org, crl):
    channel_name = org['misc']['channel_name']
    config_block_file = org['misc']['config_block_file']

    print('Creating config update payload with the generated CRL for the organization \'%s\'' % org['name'], flush=True)

    # Start the configtxlator
    # call('configtxlator start &', shell=True)
    proc = Popen('configtxlator start &', shell=True)

    print('Sleeping 5 seconds for configtxlator to start...', flush=True)
    call(['sleep', '5'])

    CTLURL = 'http://127.0.0.1:7059'
    # Convert the config block protobuf to JSON
    r = requests.post(CTLURL + '/protolator/decode/common.Block', data=open(config_block_file, 'rb').read())
    config_block = r.json()

    # Extract the config from the config block
    config = config_block['data']['data'][0]['payload']['data']['config']

    # Update crl in the config json
    updated_config = copy.deepcopy(config)

    updated_config['channel_group']['groups']['Application']['groups'][org['name']]['values']['MSP']['value']['config'][
        'revocation_list'] = [crl]

    # Create the config diff protobuf
    r = requests.post(CTLURL + '/protolator/encode/common.Config', json=config, stream=True)
    config_pb = None
    if r.status_code == 200:
        config_pb = r.content
    else:
        print(r.text, flush=True)

    r = requests.post(CTLURL + '/protolator/encode/common.Config', json=updated_config, stream=True)
    updated_config_pb = None
    if r.status_code == 200:
        updated_config_pb = r.content
    else:
        print(r.text, flush=True)

    r = requests.post(CTLURL + '/configtxlator/compute/update-from-configs', data={'channel': channel_name},
                      files={'original': config_pb, 'updated': updated_config_pb})
    config_update_pb = None
    if r.status_code == 200:
        config_update_pb = r.content
    else:
        print(r.text, flush=True)

    # call(['curl', '-X', 'POST', '--data-binary', '@config.json', CTLURL + '/protolator/encode/common.Config', '>', '/tmp/config.pb'])
    # call(['curl', '-X', 'POST', '--data-binary', '@updated_config.json', CTLURL + '/protolator/encode/common.Config', '>', '/tmp/updated_config.pb'])
    # call(['curl', '-X', 'POST', '-F', 'original=@config.pb', '-F', 'updated=@updated_config.pb', CTLURL + '/configtxlator/compute/update-from-configs', '-F', 'channel=' + channel_name, '>', '/tmp/config_update.pb'])

    # Convert the config diff protobuf to JSON
    r = requests.post(CTLURL + '/protolator/decode/common.ConfigUpdate', data=config_update_pb, stream=True)
    config_update = {}
    if r.status_code == 200:
        config_update = r.json()
    else:
        print(r.text, flush=True)
    # call(['curl', '-X', 'POST', '--data-binary', '@config_update.pb', CTLURL + '/protolator/decode/common.ConfigUpdate', '>', '/tmp/config_update.json'])

    # Create envelope protobuf container config diff to be used in the "peer channel update" command to update the channel configuration block
    config_update_as_envelope = {
        'payload': {
            'header': {
                'channel_header': {
                    'channel_id': channel_name,
                    'type': 2,
                }
            },
            'data': {
                'config_update': config_update
            }
        }
    }

    r = requests.post(CTLURL + '/protolator/encode/common.Envelope', json=config_update_as_envelope)
    if r.status_code == 200:
        with open(org['misc']['config_update_envelope_file'], 'wb') as f:
            for chunk in r:
                f.write(chunk)
    else:
        print(r.text, flush=True)
    #   echo '{"payload":{"header":{"channel_header":{"channel_id":"'"${CHANNEL_NAME}"'", "type":2}},"data":{"config_update":'$(cat config_update.json)'}}}' > config_update_as_envelope.json
    #   curl -X POST --data-binary @config_update_as_envelope.json $CTLURL/protolator/encode/common.Envelope > $CONFIG_UPDATE_ENVELOPE_FILE

    # Stop configtxlator
    proc.kill()


def updateConfigBlock(org, peer, orderer):
    org_admin_home = org['users']['admin']['home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = org['misc']['channel_name']
    config_update_envelope_file = org['misc']['config_update_envelope_file']

    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])

    tls_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer_core, org_admin_msp_dir)
    print('Updating the configuration block of the channel \'%s\'' % channel_name, flush=True)
    tls_orderer_client_dir = orderer['orderers'][0]['tls']['dir']['external'] + '/' + \
                             orderer['orderers'][0]['tls']['client']['dir']
    call(['peer', 'channel', 'update',
          '-f', config_update_envelope_file,
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['orderers'][0]['host'], 'port': orderer['orderers'][0]['port']['external']},
          '--tls',
          '--clientauth',
          '--cafile', os.path.join(tls_orderer_client_dir, orderer['orderers'][0]['tls']['client']['ca']),
          '--certfile', tls_client_dir + '/' + peer['tls']['client']['cert'],
          '--keyfile', tls_client_dir + '/' + peer['tls']['client']['key']
          ])

    # clean env variables
    clean_env_variables()


def queryAsRevokedUser(arg, org, peer, username):
    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'

    # update config path for using right core.yaml and right msp dir
    peer_core = '/substra/conf/%s/%s' % (org['name'], peer['name'])
    set_env_variables(peer_core, org_user_msp_dir)

    channel_name = org['misc']['channel_name']
    chaincode_name = org['misc']['chaincode_name']

    print(
        'Querying the chaincode in the channel \'%(CHANNEL_NAME)s\' on the peer \'%(PEER_HOST)s\' as revoked user \'%(USER_NAME)s\' ...' % {
            'CHANNEL_NAME': channel_name,
            'PEER_HOST': peer['host'],
            'USER_NAME': username,
        }, flush=True)

    starttime = int(time.time())

    tls_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
    tls_server_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['server']['dir']

    os.environ['CORE_PEER_TLS_ROOTCERT_FILE'] = os.path.join(tls_server_dir, peer['tls']['server']['ca'])
    os.environ['CORE_PEER_TLS_CERT_FILE'] = os.path.join(tls_server_dir, peer['tls']['server']['cert'])
    os.environ['CORE_PEER_TLS_KEY_FILE'] = os.path.join(tls_server_dir, peer['tls']['server']['key'])
    os.environ['CORE_PEER_TLS_CLIENTCERT_FILE'] = os.path.join(tls_client_dir, peer['tls']['client']['cert'])
    os.environ['CORE_PEER_TLS_CLIENTKEY_FILE'] = os.path.join(tls_client_dir, peer['tls']['client']['key'])
    # Continue to poll until we get a successful response or reach QUERY_TIMEOUT

    while int(time.time()) - starttime < 15:  # QUERY_TIMEOUT
        call(['sleep', '1'])

        try:
            check_output(['peer', 'chaincode', 'query',
                          '-C', channel_name,
                          '-n', chaincode_name,
                          '-c', arg,
                          '-o', '%(host)s:%(port)s' % {'host': orderer['orderers'][0]['host'], 'port': orderer['orderers'][0]['port']['external']},
                          '--tls',
                          '--clientauth',
                          ],
                         stderr=STDOUT).decode()
        except CalledProcessError as e:
            output = e.output.decode()
            # uncomment for debug
            if 'access denied' in output:
                print(
                    'Expected error occurred when the revoked user \'%(username)s\' queried the chaincode in the channel \'%(channel_name)s\'\n' % {
                        'channel_name': channel_name,
                        'username': username,
                    }, flush=True)
                # clean env variables
                clean_env_variables()
                return True
        else:
            print('.', flush=True, end='')

    err_msg = 'The revoked user %(username)s should have failed to query the chaincode in the channel \'%(channel_name)s\'' % {
        'channel_name': channel_name,
        'username': username
    }
    print(err_msg, flush=True)
    # clean env variables
    clean_env_variables()

    del os.environ['CORE_PEER_TLS_ROOTCERT_FILE']
    del os.environ['CORE_PEER_TLS_CERT_FILE']
    del os.environ['CORE_PEER_TLS_KEY_FILE']
    del os.environ['CORE_PEER_TLS_CLIENTCERT_FILE']
    del os.environ['CORE_PEER_TLS_CLIENTKEY_FILE']

    return False

def revokeFabricUserAndGenerateCRLNew():
    cacli = ca_service(target=f"https://{org['ca']['host']}:{org['ca']['port']['external']}",
                       ca_certs_path=org['ca']['certfile']['external'],
                       ca_name=org['ca']['name'])

    enrolledAdmin = cacli.enroll(org['users']['admin']['name'],
                                 org['users']['admin']['pass'])

    revoked_certs, crl = enrolledAdmin.revoke(
        org['users']['user']['name'], gencrl=True)

    print(crl)

    return crl

def fetchConfigBlockNew():
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


def createConfigUpdatePayloadWithCRLNew(config_envelope, crl):

    old_config = decode_config(config_envelope.config)
    new_config = copy.deepcopy(old_config)
    new_config['channel_group']['groups']['Application']['groups'][org['name']]['values']['MSP']['value']['config'][
        'revocation_list'] = [crl]
    # new_config['channel_group']['groups']['Application']['mod_policy'] = 'Members'

    json.dump(old_config, open('old_config.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--type', 'common.Config',
          '--input', 'old_config.json',
          '--output', 'old_config.block'
          ])

    json.dump(new_config, open('new_config.json', 'w'))
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

    json.dump(config_update_as_envelope, open('proposal.json', 'w'))

    config_tx_file = 'proposal.pb'

    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', config_tx_file])

    return config_tx_file


def updateConfigBlockNew(config_tx_file):
    org_admin = cli.get_user(org['name'], org['users']['admin']['name'])

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(cli.channel_update(
        cli.get_orderer(orderer['orderers'][0]['name']),
        org['misc']['channel_name'],
        org_admin,
        config_tx=config_tx_file))

    if res is not True:
        raise Exception('Fail to update channel')

def queryAsRevokedUserNew():

    org_user = cli.get_user(org['name'], org['users']['user']['name'])
    peers = [x['name'] for x in org['peers']]

    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(cli.chaincode_query(
        requestor=org_user,
        channel_name=org['misc']['channel_name'],
        peers=peers,
        fcn='queryObjectives',
        args=None,
        cc_name=org['misc']['chaincode_name'],
    ))

    pp.pprint(response)


def revokeFirstOrgUserNew():
    crl = revokeFabricUserAndGenerateCRLNew()

    if crl == '':
        crl = 'LS0tLS1CRUdJTiBYNTA5IENSTC0tLS0tCk1JSUJNekNCMmdJQkFUQUtCZ2dxaGtqT1BRUURBakJkTVFzd0NRWURWUVFHRXdKR1VqRVpNQmNHQTFVRUNCTVEKVEc5cGNtVXRRWFJzWVc1MGFYRjFaVEVQTUEwR0ExVUVCeE1HVG1GdWRHVnpNUTR3REFZRFZRUUtFd1Z2ZDJ0cApiakVTTUJBR0ExVUVBeE1KY21OaExXOTNhMmx1RncweE9UQTJNakF4TkRBNU5EaGFGdzB4T1RBMk1qRXhOREE1Ck5EaGFNQ2N3SlFJVVdlTURlS2RHbm5KNk0yZ0c2andRa21ocnlzMFhEVEU1TURZeU1ERTBNRGswT0ZxZ0l6QWgKTUI4R0ExVWRJd1FZTUJhQUZGY05LL0pNT1JTeTBYRUJXZGQ1eHN4ajJIaURNQW9HQ0NxR1NNNDlCQU1DQTBnQQpNRVVDSVFDTytmekZmdUZrYWRBK1IxTlVJQUpkQ0x4QzltMjhLTkJsSVRPaDlNYzNYZ0lnSERKK05IeFpFeTQ4CllMZWdzSkZraUQxSGxRT2pIajdkdkp4bndXbzRFR1U9Ci0tLS0tRU5EIFg1MDkgQ1JMLS0tLS0K'

    config_envelope = fetchConfigBlockNew()

    config_tx_file = createConfigUpdatePayloadWithCRLNew(config_envelope, crl)

    updateConfigBlockNew(config_tx_file)
    queryAsRevokedUserNew()

def revokeFirstOrgUser(cli, org, orderer):
    # Revoke the user and generate CRL using admin's credentials
    username = org['users']['user']['name']
    peer = org['peers'][0]

    crl = revokeFabricUserAndGenerateCRL(org, username)

    if crl == '':
        crl = 'LS0tLS1CRUdJTiBYNTA5IENSTC0tLS0tCk1JSUJNakNCMmdJQkFUQUtCZ2dxaGtqT1BRUURBakJkTVFzd0NRWURWUVFHRXdKR1VqRVpNQmNHQTFVRUNCTVEKVEc5cGNtVXRRWFJzWVc1MGFYRjFaVEVQTUEwR0ExVUVCeE1HVG1GdWRHVnpNUTR3REFZRFZRUUtFd1Z2ZDJ0cApiakVTTUJBR0ExVUVBeE1KY21OaExXOTNhMmx1RncweE9UQTJNakV3TnpFek5UWmFGdzB4T1RBMk1qSXdOekV6Ck5UWmFNQ2N3SlFJVUxUOFdqQmJEQkRoVWxUalJPTU9yaFE0SU1HMFhEVEU1TURZeU1UQTNNVE0xTmxxZ0l6QWgKTUI4R0ExVWRJd1FZTUJhQUZBNUxnLzhTUFRCY1NTVmVDdTZ3MnNaTTlKQ2FNQW9HQ0NxR1NNNDlCQU1DQTBjQQpNRVFDSUhhV24yQnREeUw0VjdxVXNUaWc3MHlWRUNKcExZNDk1QnNEeCt0WmRRZVlBaUFTS1VKZDZkWURKOHF4CkRHc0p2cVR1bHFvb25sTXc2ekdlUFFJVGJYZ212Zz09Ci0tLS0tRU5EIFg1MDkgQ1JMLS0tLS0K'

    # Fetch config block
    fetchConfigBlock(org, peer, orderer)

    # Create config update envelope with CRL and update the config block of the channel
    createConfigUpdatePayloadWithCRL(org, crl)
    updateConfigBlock(org, peer, orderer)

    return queryAsRevokedUser('{"Args":["queryObjectives"]}', org, peer, username)


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]
    cli = init_cli(orgs)

    org_name = 'owkin'
    org = [x for x in orgs if x['name'] == org_name][0]
    orderer = [x for x in orgs if x['type'] == 'orderer'][0]

    cli.new_channel(org['misc']['channel_name'])



    revokeFirstOrgUser(cli, org, orderer)
    #revokeFirstOrgUserNew()

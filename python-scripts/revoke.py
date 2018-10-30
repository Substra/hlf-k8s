import base64
import copy
import json
import os
import time
import subprocess

import requests

from conf import conf
from subprocess import call, check_output, STDOUT, CalledProcessError, Popen


def revokeFabricUserAndGenerateCRL(org_name, username):
    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']

    print(
        'Revoking the user \'%(username)s\' of the organization \'%(org_name)s\' with Fabric CA Client home directory set to %(org_admin_home)s and generating CRL ...' % {
            'username': username,
            'org_name': org_name,
            'org_admin_home': org_admin_home
        }, flush=True)

    call(['fabric-ca-client',
          'revoke', '-d',
          '-c', '/substra/data/orgs/' + org_name + '/admin/fabric-ca-client-config.yaml',
          '--revoke.name', username,
          '--gencrl'])


def fetchConfigBlock(org_name, peer):
    org = conf['orgs'][org_name]

    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'
    channel_name = conf['misc']['channel_name']
    orderer = conf['orderers']['orderer']
    config_block_file = conf['misc']['config_block_file']

    print('Fetching the configuration block of the channel \'%s\'' % channel_name, flush=True)

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/substra/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting the one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    call(['peer', 'channel', 'fetch', 'config', config_block_file,
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['tls']['certfile'],
          '--keyfile', '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',
          '--certfile', '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt'
          ])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def createConfigUpdatePayloadWithCRL(org_name):
    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = conf['misc']['channel_name']
    config_block_file = conf['misc']['config_block_file']

    print('Creating config update payload with the generated CRL for the organization \'%s\'' % org_name, flush=True)

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
    with open(org_admin_msp_dir + '/crls/crl.pem', 'rb') as f:
        crl = base64.b64encode(f.read()).decode('utf8')
        updated_config['channel_group']['groups']['Application']['groups'][org_name]['values']['MSP']['value'][
            'config']['revocation_list'] = [crl]

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
        with open(conf['misc']['config_update_envelope_file'], 'wb') as f:
            for chunk in r:
                f.write(chunk)
    else:
        print(r.text, flush=True)
    #   echo '{"payload":{"header":{"channel_header":{"channel_id":"'"${CHANNEL_NAME}"'", "type":2}},"data":{"config_update":'$(cat config_update.json)'}}}' > config_update_as_envelope.json
    #   curl -X POST --data-binary @config_update_as_envelope.json $CTLURL/protolator/encode/common.Envelope > $CONFIG_UPDATE_ENVELOPE_FILE

    # Stop configtxlator
    proc.kill()


def updateConfigBlock(org_name, peer):
    org = conf['orgs'][org_name]
    org_admin_home = org['admin_home']
    org_admin_msp_dir = org_admin_home + '/msp'

    channel_name = conf['misc']['channel_name']
    orderer = conf['orderers']['orderer']
    config_update_envelope_file = conf['misc']['config_update_envelope_file']

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/substra/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting the one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_admin_msp_dir

    print('Updating the configuration block of the channel \'%s\'' % channel_name, flush=True)
    call(['peer', 'channel', 'update',
          '-f', config_update_envelope_file,
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['tls']['certfile'],
          '--keyfile', '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',
          '--certfile', '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt'
          ])

    # clean env variables
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def queryAsRevokedUser(arg, org_name, peer, username):
    org = conf['orgs'][org_name]
    org_user_home = org['user_home']
    org_user_msp_dir = org_user_home + '/msp'

    # update config path for using right core.yaml
    os.environ['FABRIC_CFG_PATH'] = '/substra/conf/' + org_name + '/' + peer['name']
    # update mspconfigpath for getting one in /data
    os.environ['CORE_PEER_MSPCONFIGPATH'] = org_user_msp_dir

    def clean_env_variables():
        del os.environ['FABRIC_CFG_PATH']
        del os.environ['CORE_PEER_MSPCONFIGPATH']

    channel_name = conf['misc']['channel_name']
    chaincode_name = conf['misc']['chaincode_name']

    print(
        'Querying the chaincode in the channel \'%(CHANNEL_NAME)s\' on the peer \'%(PEER_HOST)s\' as revoked user \'%(USER_NAME)s\' ...' % {
            'CHANNEL_NAME': channel_name,
            'PEER_HOST': peer['host'],
            'USER_NAME': username,
        }, flush=True)

    starttime = int(time.time())

    # Continue to poll until we get a successful response or reach QUERY_TIMEOUT
    while int(time.time()) - starttime < 15:  # QUERY_TIMEOUT
        call(['sleep', '1'])

        try:
            check_output(['peer', 'chaincode', 'query',
                          '-C', channel_name,
                          '-n', chaincode_name, '-c', arg],
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
    return False


def revokeFirstOrgUser():
    # Revoke the user and generate CRL using admin's credentials
    org_name = 'owkin'
    org = conf['orgs'][org_name]
    username = org['users']['user']['name']
    peer = org['peers'][0]

    revokeFabricUserAndGenerateCRL('owkin', username)

    # Fetch config block
    fetchConfigBlock(org_name, peer)

    # Create config update envelope with CRL and update the config block of the channel
    createConfigUpdatePayloadWithCRL('owkin')
    updateConfigBlock(org_name, peer)

    return queryAsRevokedUser('{"Args":["queryObjects", "problem"]}', org_name, peer, username)


def run():
    res = True

    # Revoke first org user
    res = res and revokeFirstOrgUser()

    if res:
        print('Congratulations! User has been correctly revoked', flush=True)
        call(['touch', conf['misc']['run_success_revoke_file']])
    else:
        print('User revokation failed failed.', flush=True)
        call(['touch', conf['misc']['run_fail_revoke_file']])


if __name__ == "__main__":
    run()

import glob
import os
import json
import time
from subprocess import call

from utils.cli import init_cli, update_cli
from utils.run_utils import Client, ChannelAlreadyExist


# We need to retry as we cannot know when the channel is created and its genesis block is available
# Unfortunately, there is currently no other way to know when a channel has been created
def waitForPeersToJoinchannel():
    timeout = 30
    start = 0

    print('Wait For Peers to join channel', flush=True)
    print(f"Join channel {client.channel_name} with peers {[x.name for x in client.org_peers]} ...", flush=True)

    while start < timeout:
        # make peers join channel
        try:
            client.peersJoinChannel()
        except Exception as e:
            print(e)
            print('Will retry to make peers join channel', flush=True)
            start += 1
            time.sleep(1)
        else:
            print(f'Peers {[x.name for x in client.org_peers]} successfully joined channel {client.channel_name}')
            break


def add_org():
    # make current org in consortium of system channel for being able to create channel
    config_tx_file = client.createSystemUpdateProposal()
    client.signAndPushSystemUpdateProposal(config_tx_file)

    # generate channel configuration from configtx.yaml
    client.generateChannelArtifacts()

    try: # create channel
        client.createChannel()
    except ChannelAlreadyExist:  # add new org in channel, upgrade chaincode
        # make new org know channel already created
        client.cli.new_channel(client.channel_name)

        ####
        # load external confs of orgs already in consortium
        ####

        # get channel config on application channel
        old_channel_config_envelope = client.getChannelConfigBlockWithOrderer(client.channel_name)
        external_orgs = old_channel_config_envelope['config']['channel_group']['groups']['Application']['groups'].keys()
        print('external_orgs: ', list(external_orgs))

        # get conf files
        files = glob.glob(f'{substra_path}/conf/config/conf-*.json')
        files = [file_path for file_path in files
                 if file_path.split(f'{substra_path}/conf/config/conf-')[-1].split('.json')[0] in external_orgs]
        conf_externals = [json.load(open(file_path, 'r')) for file_path in files]
        # add conf_externals in cli
        update_cli(client.cli, conf_externals)

        # update channel for making it know new org
        client.generateChannelUpdate(conf, conf_externals, old_channel_config_envelope['config'])

        # make peers join channel
        waitForPeersToJoinchannel()

        # update chaincode version, as new org
        chaincode_version = client.getChaincodeVersion(conf_externals[0])
        new_chaincode_version = '%.1f' % (chaincode_version + 1.0)

        # Install chaincode on peer in each org
        orgs_mspid = []
        for conf_org in [conf] + conf_externals:
            client.installChainCodeOnPeers(conf_org, new_chaincode_version)
            orgs_mspid.append(conf_org['mspid'])

        # upgrade chaincode with new policy
        client.upgradeChainCode(conf_externals[0], orgs_mspid, new_chaincode_version, 'init')

    else:  # channel is created, install + instantiate chaincode

        # make peers join channel
        waitForPeersToJoinchannel()

        # update anchor peers if needed (normally already present in configtx.yaml)
        #client.updateAnchorPeers()

        # Install chaincode on peer in each org
        client.installChainCodeOnPeers(conf, conf['misc']['chaincode_version'])

        # Instantiate chaincode on peers (could be done on only one peer)
        client.instanciateChaincode()

    # Query chaincode
    if client.queryChaincodeFromPeers() == '[]':
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":
    org_name = os.environ.get('ORG')
    substra_path = os.environ.get('SUBSTRA_PATH')

    print(os.path.join(substra_path, 'conf/config', f'conf-{org_name}.json'))

    conf = json.load(open(os.path.join(substra_path, 'conf/config', f'conf-{org_name}.json'), 'r'))
    conf_orderer = json.load(open(os.path.join(substra_path, 'conf/config', f'conf-orderer.json'), 'r'))

    cli = init_cli([conf, conf_orderer])
    client = Client(cli, conf, conf_orderer)
    add_org()

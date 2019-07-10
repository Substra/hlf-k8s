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

    print('Wait For Peers to join channel')
    print(f"Join channel {[x.name for x in client.org_peers]} ...", flush=True)

    while start < timeout:
        # make peers join channel
        try:
            client.peersJoinChannel()
        except Exception as e:
            print(e)
            print('Will retry to make peers join channel', flush=True, end='')
            start += 1
            time.sleep(1)
        else:
            break


def add_org():
    # make current org in consortium of system channel for being able to create channel
    config_tx_file, system_channel_config = client.createSystemUpdateProposal()
    client.signAndPushSystemUpdateProposal(config_tx_file)
    time.sleep(2)  # raft time, TODO add polling

    # generate channel configuration from configtx.yaml + anchor peer configuration for future update
    client.generateChannelArtifacts()
    # create channel
    try:
        client.createChannel()
    except ChannelAlreadyExist:
        # make new org know channel already created
        client.cli.new_channel(conf['misc']['channel_name'])

        # load external conf of org already in consortiums
        external_orgs = [x for x in
                         system_channel_config['channel_group']['groups']['Consortiums']['groups']['SampleConsortium'][
                             'groups'].keys() if x != org_name]
        print('external_orgs: ', external_orgs)
        files = glob.glob('/substra/conf/config/conf-*.json')
        files = [file_path for file_path in files
                 if file_path.split('/substra/conf/config/conf-')[-1].split('.json')[0] in external_orgs]

        conf_externals = [json.load(open(file_path, 'r')) for file_path in files]
        # add conf_externals in cli
        update_cli(cli, conf_externals)

        # update channel for making it know new org (anchor peers are directly included)
        client.generateChannelUpdate(conf, conf_externals)

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

    else:
        # channel is created

        # make peers join channel
        waitForPeersToJoinchannel()

        # update anchor peers
        # TODO directly put it into generateChannelArtifacts
        client.updateAnchorPeers()

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
    org_name = os.environ.get("ORG")

    conf = json.load(open(f'/substra/conf/config/conf-{org_name}.json', 'r'))
    conf_orderer = json.load(open('/substra/conf/config/conf-orderer.json', 'r'))

    cli = init_cli([conf, conf_orderer])
    client = Client(cli, conf, conf_orderer)
    add_org()

import glob
import os
import json
from subprocess import call

from utils.run_utils import (createChannel, peersJoinChannel, updateAnchorPeers, installChainCodeOnPeers, instanciateChaincode,
                             queryChaincodeFromFirstPeerFirstOrg, generateChannelUpdate, upgradeChainCode,
                             createSystemUpdateProposal, signAndPushSystemUpdateProposal, getChaincodeVersion, generateChannelArtifacts)


def add_org(conf, conf_externals, orderer):
    generateChannelUpdate(conf, conf_externals, orderer)
    peersJoinChannel(conf, conf_orderer)

    chaincode_version = getChaincodeVersion(conf_externals[0], orderer)
    new_chaincode_version = '%.1f' % (chaincode_version + 1.0)

    # Install chaincode on peer in each org
    orgs_mspid = []
    for conf_org in [conf] + conf_externals:
        installChainCodeOnPeers(conf_org, new_chaincode_version)
        orgs_mspid.append(conf_org['mspid'])

    upgradeChainCode(conf_externals[0], '{"Args":["init"]}', orderer, orgs_mspid, new_chaincode_version)

    if queryChaincodeFromFirstPeerFirstOrg(conf, new_chaincode_version):
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


def add_org_with_channel(conf, conf_orderer):

    res = True

    generateChannelArtifacts(conf)
    config_tx_file = createSystemUpdateProposal(conf, conf_orderer)
    signAndPushSystemUpdateProposal(conf_orderer, config_tx_file)

    createChannel(conf, conf_orderer)

    peersJoinChannel(conf, conf_orderer)
    updateAnchorPeers(conf, conf_orderer)

    # Install chaincode on peer in each org
    installChainCodeOnPeers(conf, conf['misc']['chaincode_version'])

    # Instantiate chaincode on the 1st peer of the 1st org
    instanciateChaincode(conf)

    # Query chaincode from the 1st peer of the 1st org
    res = res and queryChaincodeFromFirstPeerFirstOrg(conf) == 'null'

    if res:
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":

    org_name = os.environ.get("ORG")

    conf = json.load(open('/substra/conf/config/conf-%s.json' % org_name, 'r'))
    conf_orderer = json.load(open('/substra/conf/config/conf-orderer.json', 'r'))

    if os.path.exists(conf['misc']['channel_tx_file']):
        files = glob.glob('/substra/conf/config/conf-*.json')

        # Hack to get running org
        # TODO use Discovery API
        runs = glob.glob('/substra/data/log/run-*.successful')
        successful_orgs = [file_path.split('/substra/data/log/run-')[-1].split('.successful')[0] for file_path in runs]

        files = [file_path for file_path in files
                 if file_path.split('/substra/conf/config/conf-')[-1].split('.json')[0] in successful_orgs]

        conf_externals = [json.load(open(file_path, 'r')) for file_path in files]

        add_org(conf, conf_externals, conf_orderer)
    else:
        add_org_with_channel(conf, conf_orderer)

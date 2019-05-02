import glob
import os
import json
from subprocess import call

from utils.run_utils import (createChannel, peersJoinChannel, updateAnchorPeers, installChainCodeOnPeers, instanciateChaincode,
                             waitForInstantiation, queryChaincodeFromFirstPeerFirstOrg, generateChannelUpdate, upgradeChainCode,
                             createSystemUpdateProposal, signAndPushSystemUpdateProposal, getChaincodeVersion, generateChannelArtifacts)


def add_org(conf, conf_externals, orderer):
    generateChannelUpdate(conf, conf_externals, orderer)
    peersJoinChannel(conf)

    new_chaincode_version = '%.1f' % (getChaincodeVersion(conf_externals[0], orderer) + 1.0)

    # Install chaincode on peer in each org
    orgs_mspid = []
    for conf_org in [conf] + conf_externals:
        installChainCodeOnPeers(conf_org, new_chaincode_version)
        orgs_mspid.append(conf_org['msp_id'])

    upgradeChainCode(conf_externals[0], '{"Args":["init"]}', orderer, orgs_mspid, new_chaincode_version)

    if queryChaincodeFromFirstPeerFirstOrg(conf):
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


def add_org_with_channel(conf, conf_orderer):

    res = True

    generateChannelArtifacts(conf)
    createSystemUpdateProposal(conf, conf_orderer)
    signAndPushSystemUpdateProposal(conf_orderer)

    createChannel(conf, conf_orderer)

    peersJoinChannel(conf)
    updateAnchorPeers(conf, conf_orderer)

    # Install chaincode on peer in each org
    installChainCodeOnPeers(conf, conf['misc']['chaincode_version'])

    # Instantiate chaincode on the 1st peer of the 2nd org
    instanciateChaincode(conf, conf_orderer)

    # Wait chaincode is correctly instantiated and initialized
    res = res and waitForInstantiation(conf, conf_orderer)

    # Query chaincode from the 1st peer of the 1st org
    res = res and queryChaincodeFromFirstPeerFirstOrg(conf)

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
        conf_externals = [json.load(open(file_path, 'r'))
                          for file_path in files
                          if 'orderer' not in file_path and org_name not in file_path]
        add_org(conf, conf_externals, conf_orderer)
    else:
        add_org_with_channel(conf, conf_orderer)

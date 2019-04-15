import glob
import os
import json
from subprocess import call

from utils.run_utils import (createChannel, peersJoinChannel, updateAnchorPeers, installChainCodeOnPeers, instanciateChaincode,
                             waitForInstantiation, queryChaincodeFromFirstPeerFirstOrg, generateChannelUpdate, upgradeChainCode,
                             createSystemUpdateProposal, signAndPushSystemUpdateProposal)

from utils.setup_utils import generateChannelArtifacts


def add_org(conf, conf_global):
    org = conf['orgs'][0]
    generateChannelUpdate(conf, conf_global)
    peersJoinChannel(conf)

    # Upgrade policy
    org = conf_global['orgs'][0]
    peer = org['peers'][0]
    conf_global['orgs'] += conf['orgs']
    conf_global['misc']['chaincode_version'] = '2.0'

    # Install chaincode on peer in each org
    installChainCodeOnPeers(conf_global)

    upgradeChainCode(conf_global, '{"Args":["init"]}', org, peer)

    if queryChaincodeFromFirstPeerFirstOrg(conf):
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


def add_org_with_channel(conf):
    res = True
    org = conf['orgs'][0]
    createChannel(conf, org, org['peers'][0])

    peersJoinChannel(conf)
    updateAnchorPeers(conf)

    # Install chaincode on peer in each org
    installChainCodeOnPeers(conf)

    # Instantiate chaincode on the 1st peer of the 2nd org
    instanciateChaincode(conf)

    # Wait chaincode is correctly instantiated and initialized
    res = res and waitForInstantiation(conf)

    # Query chaincode from the 1st peer of the 1st org
    res = res and queryChaincodeFromFirstPeerFirstOrg(conf)

    if res:
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":

    conf = json.load(open('/substra/conf/conf-org.json', 'r'))

    org = conf['orgs'][0]
    org_name = org['name']

    # Dirty hack to know if there is already another org or not
    files = glob.glob('/substra/conf/conf-*.json')
    files.sort(key=os.path.getmtime)
    confs = [json.load(open(file_path, 'r'))
             for file_path in files
             if 'orderer' not in file_path and 'org' not in file_path and org_name not in file_path]

    if not confs:
        generateChannelArtifacts(conf)
        createSystemUpdateProposal(conf, 'substrasystemchannel')
        signAndPushSystemUpdateProposal(conf, 'substrasystemchannel')
        add_org_with_channel(conf)
    else:
        conf_global = confs[0]
        for conf_org in confs[1:]:
            conf_global['orgs'].extend(conf_org['orgs'])
        add_org(conf, conf_global)

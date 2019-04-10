from run import createChannel, peersJoinChannel, updateAnchorPeers, installChainCodeOnPeers, instanciateChaincode, waitForInstantiation, queryChaincodeFromFirstPeerFirstOrg
from setup import generateChannelArtifacts
from run_add import generateChannelUpdate, upgradeChainCode, set_env_variables, clean_env_variables
import glob
import os
import json
from subprocess import call
from time import sleep


def run_add(conf, conf_global):

    generateChannelUpdate(conf, conf_global)

    org = conf['orgs'][0]

    # getChannelBlock(conf, org, org['peers'][0])
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


def run(conf):
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


def createSystemUpdateProposal(conf, old_block, new_block, channel_name):

    # To DO : improve proposal like link below (fetch genesis block and update it)
    # https://console.bluemix.net/docs/services/blockchain/howto/orderer_operate.html?locale=en#orderer-operate

    for block in [old_block, new_block]:
        call(['configtxlator',
              'proto_decode',
              '--input', block,
              '--type', 'common.Block',
              '--output', 'system_channelconfig.json'])

        system_channel_config = json.load(open('system_channelconfig.json', 'r'))

        # Keep useful part
        system_channel_config = system_channel_config['data']['data'][0]['payload']['data']['config']
        json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
        call(['configtxlator',
              'proto_encode',
              '--input', 'system_channelconfig.json',
              '--type', 'common.Config',
              '--output', block])

    call(['configtxlator',
          'compute_update',
          '--channel_id', channel_name,
          '--original', old_block,
          '--updated', new_block,
          '--output', 'compute_update.pb'])

    call(['configtxlator',
          'proto_decode',
          '--input', 'compute_update.pb',
          '--type', 'common.ConfigUpdate',
          '--output', 'compute_update.json'])

    # Prepare proposal
    update = json.load(open('compute_update.json', 'r'))

    print(json.dumps(update, indent=4))
    proposal = {'payload': {'header': {'channel_header': {'channel_id': channel_name,
                                                          'type': 2}},
                            'data': {'config_update': update}}}

    json.dump(proposal, open('proposal.json', 'w'))
    call(['configtxlator',
          'proto_encode',
          '--input', 'proposal.json',
          '--type', 'common.Envelope',
          '--output', 'proposal.pb'])


def signAndPushSystemUpdateProposal(conf, channel_name):
    orderer = conf['orderers'][0]
    orderer_admin_home = orderer['users']['admin']['home']
    orderer_admin_msp_dir = orderer_admin_home + '/msp'
    orderer_core = '/substra/conf/%s' % orderer['name']

    set_env_variables(orderer_core, orderer_admin_msp_dir)

    call(['peer',
          'channel', 'update',
          '--logging-level', 'DEBUG',
          '-f', 'proposal.pb',
          '-c', channel_name,
          '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
          '--tls',
          '--clientauth',
          '--cafile', orderer['ca']['certfile'],
          # https://hyperledger-fabric.readthedocs.io/en/release-1.1/enable_tls.html#configuring-tls-for-the-peer-cli
          '--keyfile', orderer['tls']['clientKey'],
          '--certfile', orderer['tls']['clientCert']
          ])

    # clean env variables
    clean_env_variables()


if __name__ == "__main__":
    conf_path = '/substra/conf/conf-org.json'

    conf = json.load(open(conf_path, 'r'))

    org = conf['orgs'][0]
    org_name = org['name']

    files = glob.glob('/substra/conf/conf-*.json')
    files.sort(key=os.path.getmtime)
    confs = [json.load(open(file_path, 'r'))
             for file_path in files
             if 'init' not in file_path and 'org' not in file_path and org_name not in file_path]
    if not confs:

        os.rename('/substra/data/genesis.block', '/substra/data/genesis_init.block')

        sleep(1)

        generateChannelArtifacts(conf)  # Generate new genesis config_block

        createSystemUpdateProposal(conf,
                                   '/substra/data/genesis_init.block',
                                   '/substra/data/genesis.block',
                                   'substrasystemchannel')
        signAndPushSystemUpdateProposal(conf, 'substrasystemchannel')

        run(conf)
    else:
        conf_global = confs[0]
        for conf_org in confs[1:]:
            conf_global['orgs'].extend(conf_org['orgs'])

        run_add(conf, conf_global)

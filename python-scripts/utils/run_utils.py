import asyncio

import json
import os

from subprocess import call, check_output

dir_path = os.path.dirname(os.path.realpath(__file__))

class Client(object):

    def __init__(self, cli):
        self.cli = cli

    def generateChannelArtifacts(self, conf):
        print(f"Generating channel configuration transaction at {conf['misc']['channel_tx_file']}", flush=True)

        call(['configtxgen',
              '-profile', 'OrgsChannel',
              '-outputCreateChannelTx', conf['misc']['channel_tx_file'],
              '-channelID', conf['misc']['channel_name']])

        print(f"Generating anchor peer update transaction for {conf['name']} at {conf['anchor_tx_file']}", flush=True)

        call(['configtxgen',
              '-profile', 'OrgsChannel',
              '-outputAnchorPeersUpdate', conf['anchor_tx_file'],
              '-channelID', conf['misc']['channel_name'],
              '-asOrg', conf['name']])

    # the signer of the channel creation transaction must have admin rights for one of the consortium orgs
    # https://stackoverflow.com/questions/45726536/peer-channel-creation-fails-in-hyperledger-fabric
    def createChannel(self, org, conf_orderer):

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self.cli.channel_create(
            self.cli.get_orderer(conf_orderer['orderers'][0]['name']),
            org['misc']['channel_name'],
            self.cli.get_user(org['name'], org['users']['admin']['name']),
            config_tx=org['misc']['channel_tx_file']))
        print('channel creation: ', res)

    def peersJoinChannel(self, org, conf_orderer):
        print(f"Join channel {[x['name'] for x in org['peers']]} ...", flush=True)

        orderer = self.cli.get_orderer(conf_orderer['orderers'][0]['name'])
        orderer_admin = self.cli.get_user(conf_orderer['name'], conf_orderer['users']['admin']['name'])
        channel_name = org['misc']['channel_name']

        loop = asyncio.get_event_loop()

        loop.run_until_complete(self.cli.channel_join(
            requestor=self.cli.get_user(org['name'], org['users']['admin']['name']),
            channel_name=channel_name,
            peers=[x['name'] for x in org['peers']],
            orderer=orderer,
            orderer_admin=orderer_admin,
        ))

    def createChannelConfig(self, org, with_anchor=True):
        org_config = check_output(['configtxgen', '-printOrg', org['name']])

        org_config = json.loads(org_config.decode('utf-8'))

        if with_anchor:
            # Add Anchor peer
            peer = org['peers'][0]
            org_config['values']['AnchorPeers'] = {'mod_policy': 'Admins',
                                                   'value': {'anchor_peers': [{'host': peer['host'],
                                                                               'port': peer['port']['internal']}]},
                                                   'version': '0'}

        return org_config

    def createUpdateProposal(self, conf, org__channel_config, my_channel_config, channel_name):

        # Keep useful part
        json.dump(my_channel_config, open('mychannelconfig.json', 'w'))

        # Add org
        my_channel_config['channel_group']['groups']['Application']['groups'][conf['name']] = org__channel_config
        json.dump(my_channel_config, open('mychannelconfigupdate.json', 'w'))

        # Compute diff
        call(['configtxlator',
              'proto_encode',
              '--input', 'mychannelconfig.json',
              '--type', 'common.Config',
              '--output', 'mychannelconfig.pb'])

        call(['configtxlator',
              'proto_encode',
              '--input', 'mychannelconfigupdate.json',
              '--type', 'common.Config',
              '--output', 'mychannelconfigupdate.pb'])

        call(['configtxlator',
              'compute_update',
              '--channel_id', channel_name,
              '--original', 'mychannelconfig.pb',
              '--updated', 'mychannelconfigupdate.pb',
              '--output', 'compute_update.pb'])

        call(['configtxlator',
              'proto_decode',
              '--input', 'compute_update.pb',
              '--type', 'common.ConfigUpdate',
              '--output', 'compute_update.json'])


        # Prepare proposal
        update = json.load(open('compute_update.json', 'r'))
        proposal = {'payload': {'header': {'channel_header': {'channel_id': channel_name,
                                                              'type': 2}},
                                'data': {'config_update': update}}}

        json.dump(proposal, open('proposal.json', 'w'))

        config_tx_file = 'proposal.pb'
        call(['configtxlator',
              'proto_encode',
              '--input', 'proposal.json',
              '--type', 'common.Envelope',
              '--output', config_tx_file])
        return config_tx_file

    def signAndPushUpdateProposal(self, orgs, conf_orderer, config_tx_file):
        orderer = conf_orderer['orderers'][0]

        signatures = []
        for org in orgs:
            # Sign
            print(f"Sign update proposal on {org['name']} ...", flush=True)

            signature = self.cli.channel_signconfigtx(config_tx_file, self.cli.get_user(org['name'], org['users']['admin']['name']))
            signatures.append(signature)
        else:
            # Push
            print(f"Send update proposal with org: {org['name']}...", flush=True)

            channel_name = org['misc']['channel_name']

            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.cli.channel_update(
                self.cli.get_orderer(orderer['name']),
                channel_name,
                self.cli.get_user(org['name'], org['users']['admin']['name']),
                config_tx=config_tx_file,
                signatures=signatures))

    def generateChannelUpdate(self, conf, external_orgs, orderer):
        org_channel_config = self.createChannelConfig(conf)

        my_channel_config_envelope = self.getChannelConfigBlockWithOrderer(orderer, conf['misc']['channel_name'])
        my_channel_config = my_channel_config_envelope['config']

        config_tx_file = self.createUpdateProposal(conf, org_channel_config, my_channel_config, conf['misc']['channel_name'])
        self.signAndPushUpdateProposal(external_orgs, orderer, config_tx_file)

    # the updater of the channel anchor transaction must have admin rights for one of the consortium orgs
    # Update the anchor peers
    def updateAnchorPeers(self, org, conf_orderer):
        print(f"Updating anchor peers...", flush=True)

        org_admin = org['users']['admin']
        orderer1 = conf_orderer['orderers'][0]

        channel_name = org['misc']['channel_name']
        orderer = self.cli.get_orderer(orderer1['name'])
        requestor = self.cli.get_user(org['name'], org_admin['name'])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.cli.channel_update(
            orderer,
            channel_name,
            requestor,
            config_tx=org['anchor_tx_file']))

    def installChainCodeOnPeers(self, org, chaincode_version):
        print(f"Installing chaincode on {[x['name'] for x in org['peers']]} ...", flush=True)

        chaincode_name = org['misc']['chaincode_name']
        chaincode_path = org['misc']['chaincode_path']

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.cli.chaincode_install(
            requestor=self.cli.get_user(org['name'], org['users']['admin']['name']),
            peers=[x['name'] for x in org['peers']],
            cc_path=chaincode_path,
            cc_name=chaincode_name,
            cc_version=chaincode_version
        ))

    def getChaincodeVersion(self, org):
        org_admin = org['users']['admin']

        channel_name = org['misc']['channel_name']
        requestor = self.cli.get_user(org['name'], org_admin['name'])

        loop = asyncio.get_event_loop()
        responses = loop.run_until_complete(self.cli.query_instantiated_chaincodes(
            requestor=requestor,
            channel_name=channel_name,
            peers=[x['name'] for x in org['peers']]
        ))

        # TODO get chaincode which has name like chaincode_name
        version = float(responses[0].chaincodes[0].version)
        return version

    def makePolicy(self, orgs_mspid):
        policy = {
            'identities': [],
            'policy': {}
        }

        for index, org_mspid in enumerate(orgs_mspid):
            policy['identities'].append({'role': {'name': 'member', 'mspId': org_mspid}})

            if len(orgs_mspid) == 1:
                policy['policy'] = {'signed-by': index}
            else:
                if not '1-of' in policy['policy']:
                    policy['policy']['1-of'] = []
                policy['policy']['1-of'].append({'signed-by': index})

        print(f'policy: {policy}', flush=True)

        return policy

    def instanciateChaincode(self, conf, args=None):

        policy = self.makePolicy([conf['mspid']])

        channel_name = conf['misc']['channel_name']
        chaincode_name = conf['misc']['chaincode_name']
        chaincode_version = conf['misc']['chaincode_version']

        requestor = self.cli.get_user(conf['name'], conf['users']['admin']['name'])
        loop = asyncio.get_event_loop()

        res = loop.run_until_complete(self.cli.chaincode_instantiate(
            requestor=requestor,
            channel_name=channel_name,
            peers=[x['name'] for x in conf['peers']],
            args=args,
            cc_name=chaincode_name,
            cc_version=chaincode_version,
            cc_endorsement_policy=policy,
            wait_for_event=True
        ))
        print(f'Instantiated chaincode with policy: {policy} and result: "{res}"')

    def upgradeChainCode(self, org, orgs_mspid, chaincode_version, fcn, args=None):
        policy = self.makePolicy(orgs_mspid)

        chaincode_name = org['misc']['chaincode_name']
        channel_name = org['misc']['channel_name']

        org_admin = org['users']['admin']

        requestor = self.cli.get_user(org['name'], org_admin['name'])

        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(self.cli.chaincode_upgrade(
            requestor=requestor,
            channel_name=channel_name,
            peers=[x['name'] for x in org['peers']],
            fcn=fcn,
            args=args,
            cc_name=chaincode_name,
            cc_version=chaincode_version,
            cc_endorsement_policy=policy,
            wait_for_event=True
        ))
        print(f'Upgraded chaincode with policy: {policy} and result: "{res}"')

    def queryChaincodeFromFirstPeerFirstOrg(self, org):
        org_admin = org['users']['admin']
        peer = org['peers'][0]

        print(f"Try to query chaincode from peer {peer['name']} on org {org['name']}", flush=True)

        channel_name = org['misc']['channel_name']
        chaincode_name = org['misc']['chaincode_name']

        requestor = self.cli.get_user(org['name'], org_admin['name'])

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.cli.chaincode_query(
            requestor=requestor,
            channel_name=channel_name,
            peers=[peer['name']],
            fcn='queryObjectives',
            args=None,
            cc_name=chaincode_name,
        ))
        print(f"Queried chaincode, result: {response}")

        return response

    def createSystemUpdateProposal(self, org, conf_orderer):
        # https://console.bluemix.net/docs/services/blockchain/howto/orderer_operate.html?locale=en#orderer-operate

        channel_name = org['misc']['system_channel_name']
        org_config = self.createChannelConfig(org, with_anchor=False)
        system_channel_config_envelope = self.getChannelConfigBlockWithOrderer(conf_orderer, conf_orderer['misc']['system_channel_name'])
        system_channel_config = system_channel_config_envelope['config']

        json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
        call(['configtxlator',
              'proto_encode',
              '--input', 'system_channelconfig.json',
              '--type', 'common.Config',
              '--output', 'systemchannelold.block'])

        # Update useful part
        system_channel_config['channel_group']['groups']['Consortiums']['groups']['SampleConsortium']['groups'][
            org['name']] = org_config
        json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
        call(['configtxlator',
              'proto_encode',
              '--input', 'system_channelconfig.json',
              '--type', 'common.Config',
              '--output', 'systemchannelupdate.block'])

        # Compute update
        call(f'configtxlator compute_update --channel_id {channel_name}'
             f' --original systemchannelold.block'
             f' --updated systemchannelupdate.block'
             f' | '
             f'configtxlator proto_decode --type common.ConfigUpdate'
             f' --output compute_update.json',
             shell=True)

        # Prepare proposal
        update = json.load(open('compute_update.json', 'r'))

        proposal = {'payload': {'header': {'channel_header': {'channel_id': channel_name,
                                                              'type': 2}},
                                'data': {'config_update': update}}}

        json.dump(proposal, open('proposal.json', 'w'))

        config_tx_file = 'proposal.pb'

        call(['configtxlator',
              'proto_encode',
              '--input', 'proposal.json',
              '--type', 'common.Envelope',
              '--output', config_tx_file])

        return config_tx_file

    def getChannelConfigBlockWithOrderer(self, conf, channel_name):
        print('Will getChannelConfigBlockWithOrderer', flush=True)

        orderer = self.cli.get_orderer(conf['orderers'][0]['name'])
        requestor = self.cli.get_user(conf['name'], conf['users']['admin']['name'])

        loop = asyncio.get_event_loop()
        config_envelope = loop.run_until_complete(self.cli.get_channel_config_with_orderer(
            requestor=requestor,
            channel_name=channel_name,
            orderer=orderer,
        ))

        print('got ChannelConfigBlockWithOrderer', flush=True)

        return config_envelope

    def signAndPushSystemUpdateProposal(self, org, config_tx_file):
        print('signAndPushSystemUpdateProposal')

        channel_name = org['misc']['system_channel_name']

        orderer = self.cli.get_orderer(org['orderers'][0]['name'])
        requestor = self.cli.get_user(org['name'], org['users']['admin']['name'])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.cli.channel_update(
            orderer,
            channel_name,
            requestor,
            config_tx=config_tx_file))

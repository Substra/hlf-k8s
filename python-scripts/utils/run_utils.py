import asyncio

import json
import os
import random

from subprocess import call, check_output

from hfc.util.policies import s2d

dir_path = os.path.dirname(os.path.realpath(__file__))


class ChannelAlreadyExist(Exception):
    pass


class Client(object):

    def __init__(self, cli, conf, conf_orderer):
        self.cli = cli
        self.orderer = random.choice(list(self.cli._orderers.values()))
        self.orderer_admin = self.cli.get_user(conf_orderer['name'], conf_orderer['users']['admin']['name'])

        self.org = self.cli._organizations[conf['name']]
        self.org_peers = [p for p in self.cli._peers.values() if p.name in [x['name'] for x in conf['peers']]]

        self.org_admin = self.cli.get_user(conf['name'], conf['users']['admin']['name'])
        self.org_user = self.cli.get_user(conf['name'], conf['users']['user']['name'])
        self.config_tx = conf['anchor_tx_file']
        self.mspid = conf['mspid']

        self.system_channel_name = conf['misc']['system_channel_name']
        self.channel_name = conf['misc']['channel_name']
        self.channel_tx_file = conf['misc']['channel_tx_file']
        self.config_tx_path = conf['misc']['configtx-config-path']
        self.chaincode_name = conf['misc']['chaincode_name']
        self.chaincode_path = conf['misc']['chaincode_path']
        self.chaincode_version = conf['misc']['chaincode_version']

        self.loop = asyncio.get_event_loop()

    def generateChannelArtifacts(self):
        print(f"Generating channel configuration transaction at {self.channel_tx_file}", flush=True)

        call(['configtxgen',
              '-configPath', self.config_tx_path,
              '-profile', 'OrgsChannel',
              '-outputCreateChannelTx', self.channel_tx_file,
              '-channelID', self.channel_name])

    # the signer of the channel creation transaction must have admin rights for one of the consortium orgs
    # https://stackoverflow.com/questions/45726536/peer-channel-creation-fails-in-hyperledger-fabric
    def createChannel(self):
        try:
            res = self.loop.run_until_complete(self.cli.channel_create(
                self.orderer,
                self.channel_name,
                self.org_admin,
                config_tx=self.channel_tx_file))
            print('channel creation: ', res)
        except:
            raise ChannelAlreadyExist('Failed to create channel')

    def peersJoinChannel(self):
        self.loop.run_until_complete(self.cli.channel_join(
            requestor=self.org_admin,
            channel_name=self.channel_name,
            peers=self.org_peers,
            orderer=self.orderer,
        ))

    def createChannelConfig(self):
        org_config = check_output(['configtxgen',
                                   '-configPath', self.config_tx_path,
                                   '-printOrg', self.org._name
                                   ])
        return json.loads(org_config.decode('utf-8'))

    def createUpdateProposal(self, conf, new_channel_config, old_channel_config):

        # Keep useful part
        json.dump(old_channel_config, open('oldchannelconfig.json', 'w'))

        # Add org
        old_channel_config['channel_group']['groups']['Application']['groups'][conf['name']] = new_channel_config
        json.dump(old_channel_config, open('newchannelconfig.json', 'w'))

        # Compute diff
        call(['configtxlator',
              'proto_encode',
              '--input', 'oldchannelconfig.json',
              '--type', 'common.Config',
              '--output', 'oldchannelconfig.pb'])

        call(['configtxlator',
              'proto_encode',
              '--input', 'newchannelconfig.json',
              '--type', 'common.Config',
              '--output', 'newchannelconfig.pb'])

        call(['configtxlator',
              'compute_update',
              '--channel_id', self.channel_name,
              '--original', 'oldchannelconfig.pb',
              '--updated', 'newchannelconfig.pb',
              '--output', 'compute_update.pb'])

        call(['configtxlator',
              'proto_decode',
              '--input', 'compute_update.pb',
              '--type', 'common.ConfigUpdate',
              '--output', 'compute_update.json'])

        # Prepare proposal
        update = json.load(open('compute_update.json', 'r'))
        proposal = {'payload': {'header': {'channel_header': {'channel_id': self.channel_name,
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

    def signAndPushUpdateProposal(self, conf_externals, config_tx_file):
        signatures = []
        for conf in conf_externals:
            # Sign
            print(f"Sign update proposal on {conf['name']} ...", flush=True)

            org_admin = self.cli.get_user(conf['name'], conf['users']['admin']['name'])

            signature = self.cli.channel_signconfigtx(config_tx_file, org_admin)
            signatures.append(signature)
        else:
            # Push with last one
            print(f"Send update proposal with org: {conf['name']}...", flush=True)

            self.loop.run_until_complete(self.cli.channel_update(
                self.orderer,
                self.channel_name,
                org_admin,
                config_tx=config_tx_file,
                signatures=signatures))

    def generateChannelUpdate(self, conf, conf_externals, old_channel_config):
        new_channel_config = self.createChannelConfig()

        # Add Anchor peer
        peer = random.choice(self.org_peers)
        host, port = peer.endpoint.split(':')
        new_channel_config['values']['AnchorPeers'] = {
            'mod_policy': 'Admins',
            'value': {
                'anchor_peers': [
                    {
                        'host': host,
                        'port': port
                    }
                ]},
            'version': '0'
        }

        config_tx_file = self.createUpdateProposal(conf, new_channel_config, old_channel_config)
        self.signAndPushUpdateProposal(conf_externals, config_tx_file)

    # the updater of the channel anchor transaction must have admin rights for one of the consortium orgs
    # Update the anchor peers
    def updateAnchorPeers(self):
        print(f"Updating anchor peers...", flush=True)
        self.loop.run_until_complete(self.cli.channel_update(
            self.orderer,
            self.channel_name,
            self.org_admin,
            config_tx=self.config_tx))

    def installChainCodeOnPeers(self, conf, chaincode_version):

        org_admin = self.cli.get_user(conf['name'], conf['users']['admin']['name'])
        peers = [x['name'] for x in conf['peers']]

        print(f"Installing chaincode on {peers} ...", flush=True)

        kwargs = {
            'requestor': org_admin,
            'peers': peers,
            'cc_path': self.chaincode_path,
            'cc_name': self.chaincode_name,
            'cc_version': chaincode_version,
        }

        self.loop.run_until_complete(self.cli.chaincode_install(**kwargs))

    def getChaincodeVersion(self, conf):
        org_admin = self.cli.get_user(conf['name'], conf['users']['admin']['name'])
        peers = [x['name'] for x in conf['peers']]

        responses = self.loop.run_until_complete(self.cli.query_instantiated_chaincodes(
            requestor=org_admin,
            channel_name=self.channel_name,
            peers=peers
        ))

        chaincodes = responses[0].chaincodes
        for cc in chaincodes:
            if self.chaincode_name == cc.name:
                return float(cc.version)
        else:
            raise Exception(f'Could not find valid chaincode version, expected version: "{self.chaincode_name}"')

    def makePolicy(self, orgs_mspid):
        roles =[f"'{x}.member'" for x in orgs_mspid]
        policy = f"OR({', '.join(roles)})"
        print('policy: ', policy, flush=True)

        return s2d().parse(policy)

    def instanciateChaincode(self, args=None):

        policy = self.makePolicy([self.mspid])

        res = self.loop.run_until_complete(self.cli.chaincode_instantiate(
            requestor=self.org_admin,
            channel_name=self.channel_name,
            peers=self.org_peers,
            args=args,
            cc_name=self.chaincode_name,
            cc_version=self.chaincode_version,
            cc_endorsement_policy=policy,
            wait_for_event=True
        ))
        print(f'Instantiated chaincode with policy: {policy} and result: "{res}"')

    def upgradeChainCode(self, conf, orgs_mspid, chaincode_version, fcn, args=None):
        policy = self.makePolicy(orgs_mspid)

        org_admin = self.cli.get_user(conf['name'], conf['users']['admin']['name'])
        peers = [x['name'] for x in conf['peers']]

        res = self.loop.run_until_complete(self.cli.chaincode_upgrade(
            requestor=org_admin,
            channel_name=self.channel_name,
            peers=peers,
            fcn=fcn,
            args=args,
            cc_name=self.chaincode_name,
            cc_version=chaincode_version,
            cc_endorsement_policy=policy,
            wait_for_event=True
        ))
        print(f'Upgraded chaincode with policy: {policy} and result: "{res}"')

    def queryChaincodeFromPeers(self):
        print(f"Try to query chaincode from peer {[x.name for x in self.org_peers]} on org {self.org._name}",
              flush=True)

        response = self.loop.run_until_complete(self.cli.chaincode_query(
            requestor=self.org_user,
            channel_name=self.channel_name,
            peers=self.org_peers,
            fcn='queryObjectives',
            args=None,
            cc_name=self.chaincode_name,
        ))
        print(f"Queried chaincode, result: {response}")

        return response

    def createSystemUpdateProposal(self):
        # https://console.bluemix.net/docs/services/blockchain/howto/orderer_operate.html?locale=en#orderer-operate

        org_config = self.createChannelConfig()
        system_channel_config_envelope = self.getChannelConfigBlockWithOrderer(self.system_channel_name)
        system_channel_config = system_channel_config_envelope['config']

        json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
        call(['configtxlator',
              'proto_encode',
              '--input', 'system_channelconfig.json',
              '--type', 'common.Config',
              '--output', 'systemchannelold.block'])

        # Update useful part
        system_channel_config['channel_group']['groups']['Consortiums']['groups']['SampleConsortium']['groups'][
            self.org._name] = org_config
        json.dump(system_channel_config, open('system_channelconfig.json', 'w'))
        call(['configtxlator',
              'proto_encode',
              '--input', 'system_channelconfig.json',
              '--type', 'common.Config',
              '--output', 'systemchannelupdate.block'])

        # Compute update
        call(f'configtxlator compute_update --channel_id {self.system_channel_name}'
             f' --original systemchannelold.block'
             f' --updated systemchannelupdate.block'
             f' | '
             f'configtxlator proto_decode --type common.ConfigUpdate'
             f' --output compute_update.json',
             shell=True)

        # Prepare proposal
        update = json.load(open('compute_update.json', 'r'))

        proposal = {'payload': {'header': {'channel_header': {'channel_id': self.system_channel_name,
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

    def getChannelConfigBlockWithOrderer(self, channel_name):
        print('Will getChannelConfigBlockWithOrderer', flush=True)

        config_envelope = self.loop.run_until_complete(self.cli.get_channel_config_with_orderer(
            requestor=self.orderer_admin,
            channel_name=channel_name,
            orderer=self.orderer,
        ))

        print('got ChannelConfigBlockWithOrderer', flush=True)

        return config_envelope

    def signAndPushSystemUpdateProposal(self, config_tx_file):
        print('signAndPushSystemUpdateProposal', flush=True)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.cli.channel_update(
            self.orderer,
            self.system_channel_name,
            self.orderer_admin,
            config_tx=config_tx_file))

import os
import asyncio
import glob
import json


from hfc.fabric.peer import Peer
from hfc.fabric.user import create_user
from hfc.util.keyvaluestore import FileKeyValueStore
from hfc.fabric.block_decoder import decode_fabric_MSP_config, decode_fabric_peers_info, decode_fabric_endpoints

from utils.cli import init_cli
from utils.run_utils import Client

ORG = 'owkin'
SUBSTRA_PATH = '/substra'

LEDGER_CONFIG_FILE = os.environ.get('LEDGER_CONFIG_FILE', f'/substra/conf/{ORG}/substrabac/conf.json')
LEDGER = json.load(open(LEDGER_CONFIG_FILE, 'r'))

PEER_PORT = LEDGER['peer']['port'][os.environ.get('SUBSTRABAC_PEER_PORT', 'external')]

LEDGER['requestor'] = create_user(
    name=LEDGER['client']['name'],
    org=LEDGER['client']['org'],
    state_store=FileKeyValueStore(LEDGER['client']['state_store']),
    msp_id=LEDGER['client']['msp_id'],
    key_path=glob.glob(LEDGER['client']['key_path'])[0],
    cert_path=LEDGER['client']['cert_path']
)


def deserialize_config(config_result):

    results = {'msps': {},
               'orderers': {}}

    for mspid in config_result.msps:
        results['msps'][mspid] = decode_fabric_MSP_config(
            config_result.msps[mspid].SerializeToString()
        )

    for mspid in config_result.orderers:
        results['orderers'][mspid] = decode_fabric_endpoints(
            config_result.orderers[mspid].endpoint
        )

    return results


def deserialize_members(members):
    peers = []

    for mspid in members.peers_by_org:
        peer = decode_fabric_peers_info(
            members.peers_by_org[mspid].peers
        )
        peers.append(peer)

    return peers


def deserialize_discovery(response):
    results = {
        'config': None,
        'members': []
    }

    for res in response.results:
        if res.config_result:
            results['config'] = deserialize_config(res.config_result)

        if res.members:
            results['members'].extend(deserialize_members(res.members))

    return results


def get_hfc_client():

    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    #
    # client = Client()
    # channel = client.new_channel(LEDGER['channel_name'])
    #
    # # Add peer from substrabac ledger config file
    # peer = Peer(name=LEDGER['peer']['name'])
    # peer.init_with_bundle({
    #     'url': f'{LEDGER["peer"]["host"]}:{PEER_PORT}',
    #     'grpcOptions': LEDGER['peer']['grpcOptions'],
    #     'tlsCACerts': {'path': LEDGER['peer']['tlsCACerts']},
    #     'clientKey': {'path': LEDGER['peer']['clientKey']},
    #     'clientCert': {'path': LEDGER['peer']['clientCert']},
    # })
    # client._peers[LEDGER['peer']['name']] = peer

    results = client.loop.run_until_complete(
        cli.chaincode_invoke(
            client.org_admin,
            client.channel_name,
            client.org_peers,
            [''],
            cc_name='cscc',
            fcn='GetChannels',
        )
    )
    print(results)
    #
    # # Get living channels
    # results = loop.run_until_complete(
    #     client.chaincode_invoke(
    #         LEDGER['requestor'],
    #         channel.name,
    #         [peer],
    #         [''],
    #         cc_name='cscc',
    #         fcn='GetChannels',
    #     )
    # )
    # print(results)


    # Discover orderers and peers from channel discovery
    # results = loop.run_until_complete(
    #     channel._discovery(
    #         LEDGER['requestor'],
    #         peer,
    #         config=True,
    #         local=False
    #     )
    # )
    #results = deserialize_discovery(results)
    #pprint(results)


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]

    cli = init_cli(orgs)

    # add channel on cli
    channel_name = orgs[0]['misc']['channel_name']
    cli.new_channel(channel_name)

    conf = json.load(open('/substra/conf/config/conf-%s.json' % ORG, 'r'))
    conf_orderer = json.load(open('/substra/conf/config/conf-orderer.json', 'r'))
    client = Client(cli, conf, conf_orderer)

    get_hfc_client()

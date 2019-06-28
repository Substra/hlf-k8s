import asyncio
import glob


from hfc.fabric.peer import Peer
from hfc.fabric.user import create_user
from hfc.util.keyvaluestore import FileKeyValueStore
from hfc.fabric.block_decoder import decode_fabric_MSP_config, decode_fabric_peers_info, decode_fabric_endpoints


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


def get_hfc_client(client):

    channel = client.cli.new_channel(client.channel_name)

    peer = client.org_peers[0]
    requestor = client.org_admin

    # Discover orderers and peers from channel discovery
    results = client.loop.run_until_complete(
        channel._discovery(
            requestor,
            peer,
            config=True,
            local=True
        )
    )
    results = deserialize_discovery(results)

    return results

import os

from hfc.fabric import Client
from hfc.fabric.orderer import Orderer
from hfc.fabric.organization import create_org
from hfc.fabric.peer import Peer
from hfc.fabric.user import create_user
from hfc.util.crypto.crypto import Rsa, ecies
from hfc.util.keyvaluestore import FileKeyValueStore

SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')


def update_cli(cli, orgs):
    for org in orgs:

        # add organization
        cli._organizations.update({org['name']: create_org(org['name'], org, cli.state_store)})

        for user_name in org['users'].keys():
            org_user = org['users'][user_name]
            org_user_home = org_user['home']
            org_user_msp_dir = os.path.join(org_user_home, 'msp')

            # register user
            user_cert_path = os.path.join(org_user_msp_dir, 'signcerts', 'cert.pem')
            user_key_path = os.path.join(org_user_msp_dir, 'keystore', 'key.pem')

            crypto_suite = ecies()
            if 'orderers' not in org:
                crypto_suite = Rsa()

            user = create_user(name=org_user['name'],
                               org=org['name'],
                               state_store=cli.state_store,
                               msp_id=org['mspid'],
                               cert_path=user_cert_path,
                               key_path=user_key_path,
                               crypto_suite=crypto_suite)

            cli._organizations[org['name']]._users.update({org_user['name']: user})

        # register orderer
        if 'orderers' in org:
            for o in org['orderers']:
                tls_orderer_client_dir = os.path.join(o['tls']['dir']['external'], o['tls']['client']['dir'])
                orderer = Orderer(o['name'],
                                  endpoint=f"{o['host']}:{o['port']['internal']}",
                                  tls_ca_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['ca']),
                                  client_cert_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['cert']),
                                  client_key_file=os.path.join(tls_orderer_client_dir, o['tls']['client']['key']),
                                  )

                cli._orderers.update({o['name']: orderer})

        # register peers
        if 'peers' in org:
            for peer in org['peers']:
                tls_peer_client_dir = os.path.join(peer['tls']['dir']['external'], peer['tls']['client']['dir'])

                port = peer['port'][os.environ.get('ENV', 'external')]
                p = Peer(name=peer['name'],
                         endpoint=f"{peer['host']}:{port}",
                         tls_ca_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['ca']),
                         client_cert_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['cert']),
                         client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
                cli._peers.update({peer['name']: p})

        # register system channel
        system_channel_name = org['misc']['system_channel_name']
        if not cli.get_channel(system_channel_name):
            cli.new_channel(system_channel_name)

    return cli


def init_cli(orgs):
    cli = Client()
    cli._state_store = FileKeyValueStore('/tmp/kvs/')

    return update_cli(cli, orgs)

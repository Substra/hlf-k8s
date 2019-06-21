import os

from hfc.fabric import Client
from hfc.fabric.orderer import Orderer
from hfc.fabric.organization import create_org
from hfc.fabric.peer import Peer
from hfc.fabric.user import create_user
from hfc.util.keyvaluestore import FileKeyValueStore

SUBSTRA_PATH = '/substra'


def init_cli(orgs):
    cli = Client()
    cli._state_store = FileKeyValueStore('/tmp/kvs/')

    for org in [x for x in orgs if x['type'] == 'orderer']:
        # add orderer organization
        cli._organizations.update(
            {org['name']: create_org(org['name'], org, cli.state_store)})

        # add orderer admin
        orderer_org_admin = org['users']['admin']
        orderer_org_admin_home = orderer_org_admin['home']
        orderer_org_admin_msp_dir = os.path.join(orderer_org_admin_home, 'msp')
        # register admin
        orderer_admin_cert_path = os.path.join(
            orderer_org_admin_msp_dir, 'signcerts', 'cert.pem')
        orderer_admin_key_path = os.path.join(
            orderer_org_admin_msp_dir, 'keystore', 'key.pem')
        orderer_admin = create_user(name=orderer_org_admin['name'],
                                    org=org['name'],
                                    state_store=cli.state_store,
                                    msp_id=org['mspid'],
                                    cert_path=orderer_admin_cert_path,
                                    key_path=orderer_admin_key_path)
        cli._organizations[org['name']]._users.update(
            {orderer_org_admin['name']: orderer_admin})

        # add real orderer from orderer organization
        for o in org['orderers']:
            tls_orderer_client_dir = os.path.join(
                o['tls']['dir']['external'], o['tls']['client']['dir'])
            orderer = Orderer(o['name'],
                              endpoint=f"{o['host']}:{o['port']['internal']}",
                              tls_ca_cert_file=os.path.join(
                                  tls_orderer_client_dir, o['tls']['client']['ca']),
                              client_cert_file=os.path.join(
                                  tls_orderer_client_dir, o['tls']['client']['cert']),
                              client_key_file=os.path.join(
                                  tls_orderer_client_dir, o['tls']['client']['key']),
                              )

            cli._orderers.update({o['name']: orderer})

        system_channel_name = org['misc']['system_channel_name']
        if not cli.get_channel(system_channel_name):
            cli.new_channel(system_channel_name)

    for org in [x for x in orgs if x['type'] == 'client']:

        # add orderer organization
        cli._organizations.update(
            {org['name']: create_org(org['name'], org, cli.state_store)})

        for user_name in org['users'].keys():
            org_user = org['users'][user_name]
            org_user_home = org_user['home']
            org_user_msp_dir = os.path.join(org_user_home, 'msp')

            # register user
            user_cert_path = os.path.join(
                org_user_msp_dir, 'signcerts', 'cert.pem')
            user_key_path = os.path.join(
                org_user_msp_dir, 'keystore', 'key.pem')

            user = create_user(name=org_user['name'],
                               org=org['name'],
                               state_store=cli.state_store,
                               msp_id=org['mspid'],
                               cert_path=user_cert_path,
                               key_path=user_key_path)

            cli._organizations[org['name']]._users.update(
                {org_user['name']: user})

        # register peers
        for peer in org['peers']:
            tls_peer_client_dir = os.path.join(
                peer['tls']['dir']['external'], peer['tls']['client']['dir'])

            port = peer['port'][os.environ.get('ENV', 'external')]
            p = Peer(name=peer['name'],
                     endpoint=f"{peer['host']}:{port}",
                     tls_ca_cert_file=os.path.join(
                         tls_peer_client_dir, peer['tls']['client']['ca']),
                     client_cert_file=os.path.join(
                         tls_peer_client_dir, peer['tls']['client']['cert']),
                     client_key_file=os.path.join(tls_peer_client_dir, peer['tls']['client']['key']))
            cli._peers.update({peer['name']: p})

        system_channel_name = org['misc']['system_channel_name']
        if not cli.get_channel(system_channel_name):
            cli.new_channel(system_channel_name)

    return cli

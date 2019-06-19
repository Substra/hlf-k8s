
import pprint
import json
import glob
import os
import asyncio

from utils.cli import init_cli
from hfc.fabric import Client
from hfc.fabric_ca.caservice import ca_service

SUBSTRA_PATH = '/substra'

pp = pprint.PrettyPrinter(indent=2)

# def revoke_user(organization_name, admin, user):
#     revoked_certs, crl = admin.revoke(user)


def run(cli, org):
    cacli = ca_service(target=f"https://{org['ca']['host']}:{org['ca']['port']['external']}",
                       ca_certs_path=org['ca']['certfile']['external'],
                       ca_name=org['ca']['name'])

    enrolledAdmin = cacli.enroll(org['users']['admin']['name'],
                                 org['users']['admin']['pass'])

    RevokedCerts, CRL = enrolledAdmin.revoke(
        org['users']['user']['name'], gencrl=True)

    pp.pprint(RevokedCerts)
    pp.pprint(CRL)

    requestor = cli.get_user(org['name'], org['users']['user']['name'])

    # loop = asyncio.get_event_loop()
    # config_envelope = loop.run_until_complete(cli.get_channel_config(
    #     requestor=requestor,
    #     channel_name=channel_name,
    #     peers=peers
    # ))

    # pp.pprint(config_envelope)


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]
    # pp.pprint(orgs)
    cli = init_cli(orgs)
    cli.new_channel(orgs[0]['misc']['channel_name'])

    run(cli, orgs[1])

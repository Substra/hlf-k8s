
import pprint
import json
import glob
import os

from utils.cli import init_cli
from hfc.fabric import Client
from hfc.fabric_ca.caservice import ca_service

SUBSTRA_PATH = '/substra'

pp = pprint.PrettyPrinter(indent=2)

# def revoke_user(organization_name, admin, user):
#     revoked_certs, crl = admin.revoke(user)


def run(cli, org):
    organization_admin_user = cli.get_user(
        org['name'], org['users']['admin']['name'])

    target = f"https://{org['ca']['host']}:{org['ca']['port']['external']}"
    print(target)

    cacli = ca_service(target=target,
                       ca_certs_path=org['ca']['certfile']['external'],
                       ca_name=org['ca']['name'])

    enrolledAdmin = cacli.enroll(org['users']['admin']['name'],
                                 org['users']['admin']['pass'])
    print(enrolledAdmin)

    RevokedCerts, CRL = enrolledAdmin.revoke(org['users']['user']['name'])
    pp.pprint(RevokedCerts)
    pp.pprint(CRL)


if __name__ == "__main__":
    files = glob.glob(f'{SUBSTRA_PATH}/conf/config/conf-*.json')
    files.sort(key=os.path.getmtime)
    orgs = [json.load(open(file_path, 'r')) for file_path in files]
    pp.pprint(orgs)
    cli = init_cli(orgs)
    cli.new_channel(orgs[0]['misc']['channel_name'])

    run(cli, orgs[1])

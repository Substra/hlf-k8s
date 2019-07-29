import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

admin = {
    'name': 'admin-clb',
    'pass': 'admin-clbpw',
    'home': f'{SUBSTRA_PATH}/data/orgs/clb/admin',
    'cert': f'{SUBSTRA_PATH}/data/orgs/clb/admin/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/clb/admin/msp/keystore/key.pem',
}

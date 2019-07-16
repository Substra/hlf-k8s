import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

user = {
    'name': 'user-clb',
    'pass': 'user-clbpw',
    'home': f'{SUBSTRA_PATH}/data/orgs/clb/user',
    'cert': f'{SUBSTRA_PATH}/data/orgs/clb/user/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/clb/user/msp/keystore/key.pem',
}

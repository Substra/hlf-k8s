import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

user = {
    'name': 'user-owkin',
    'pass': 'user-owkinpw',
    'home': f'{SUBSTRA_PATH}/data/orgs/owkin/user',
    'cert': f'{SUBSTRA_PATH}/data/orgs/owkin/user/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/owkin/user/msp/keystore/key.pem',
}

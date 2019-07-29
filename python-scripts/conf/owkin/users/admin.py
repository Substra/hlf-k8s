import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

admin = {
    'name': 'admin-owkin',
    'pass': 'admin-owkinpw',
    'home': f'{SUBSTRA_PATH}/data/orgs/owkin/admin',
    'cert': f'{SUBSTRA_PATH}/data/orgs/owkin/admin/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/owkin/admin/msp/keystore/key.pem',
}

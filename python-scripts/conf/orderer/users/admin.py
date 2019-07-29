import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

admin = {
    'name': 'admin-orderer',
    'pass': 'admin-ordererpw',
    'home': f'{SUBSTRA_PATH}/data/orgs/orderer/admin',
    'cert': f'{SUBSTRA_PATH}/data/orgs/orderer/admin/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/orderer/admin/msp/keystore/key.pem',
}

import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

admin = {
    'name': 'admin-chu-nantes',
    'pass': 'admin-chu-nantespw',
    'home': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/admin',
    'cert': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/admin/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/admin/msp/keystore/key.pem',
}

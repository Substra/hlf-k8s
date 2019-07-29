import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

user = {
    'name': 'user-chu-nantes',
    'pass': 'user-chu-nantespw',
    'home': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/user',
    'cert': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/user/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/user/msp/keystore/key.pem',
}

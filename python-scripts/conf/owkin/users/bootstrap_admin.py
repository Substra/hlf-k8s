import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

bootstrap_admin = {
    'name': 'admin',
    'pass': 'adminpw',
    'home': f'{SUBSTRA_PATH}/data/orgs/owkin/bootstrap_admin',
}

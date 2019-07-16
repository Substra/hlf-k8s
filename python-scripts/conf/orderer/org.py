import os
from .users.bootstrap_admin import bootstrap_admin
from .users.admin import admin
from orderer.orderers.orderer1 import orderer1

SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

orderer = {
    'type': 'orderer',
    'name': 'orderer',
    'mspid': 'ordererMSP',
    'broadcast_dir': {
            'external': f'{SUBSTRA_PATH}/data/log/broadcast',
            'internal': '/etc/hyperledger/fabric/broadcast'
    },
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a
        # example file with this name is already present in the docker
        # image, do not forget to remove these examples files in your
        # docker CMD overriding if naming the same way
        'certfile': {
            'external': f'{SUBSTRA_PATH}/data/orgs/orderer/tls-ca-cert.pem',
            'internal': '/etc/hyperledger/fabric/ca/tls-ca-cert.pem'
        },
        'clientkey': ''
    },
    'ca': {
        'name': 'rca-orderer',
        'host': 'rca-orderer',
        'certfile': {
            'external': f'{SUBSTRA_PATH}/data/orgs/orderer/ca-cert.pem',
            'internal': '/etc/hyperledger/fabric/ca/ca-cert.pem'
        },
        'keyfile': {
            'external': f'{SUBSTRA_PATH}/data/orgs/orderer/ca-key.pem',
            'internal': '/etc/hyperledger/fabric/ca/ca-key.pem'
        },
        'port': {
            'internal': 7054,
            'external': 9054
        },
        'url': 'https://rca-orderer:7054',
        'logfile': f'{SUBSTRA_PATH}/data/log/rca-orderer.log',
        'server-config-path': f'{SUBSTRA_PATH}/conf/orderer/fabric-ca-server-config.yaml',
        'client-config-path': f'{SUBSTRA_PATH}/conf/orderer/fabric-ca-client-config.yaml',
        'affiliations': {
            'owkin': ['paris']
        },
        'users': {
            'bootstrap_admin': bootstrap_admin,
        },
    },
    'users': {
        'admin': admin,
    },
    'csr': {
        'cn': 'rca-orderer',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-orderer'],
        'names': [
            {'C': 'FR',
             'ST': 'Ile-de-France',
             'L': 'Paris',
             'O': 'owkin',
             'OU': None}
        ],
    },
    'core_dir': {
        'internal': '/etc/hyperledger/fabric',
    },
    'orderers': [orderer1],
}

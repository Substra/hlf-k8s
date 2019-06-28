from .peers.peer1 import peer1
from .peers.peer2 import peer2
from .users.admin import admin
from .users.bootstrap_admin import bootstrap_admin
from .users.user import user

chunantes = {
    'type': 'client',
    'name': 'chu-nantes',
    'mspid': 'chu-nantesMSP',
    'anchor_tx_file': '/substra/data/orgs/chu-nantes/anchors.tx',
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in
        # the docker image, do not forget to remove these examples files if naming the same way
        'certfile': {
            'external': '/substra/data/orgs/chu-nantes/tls-ca-cert.pem',
            'internal': '/etc/hyperledger/fabric/ca/tls-ca-cert.pem'
        },
        'clientkey': ''
    },
    'ca': {
        'name': 'rca-chu-nantes',
        'host': 'rca-chu-nantes',
        'certfile': {
            'external': '/substra/data/orgs/chu-nantes/ca-cert.pem',
            'internal': '/etc/hyperledger/fabric/ca/ca-cert.pem'
        },
        'keyfile': {
            'external': '/substra/data/orgs/chu-nantes/ca-key.pem',
            'internal': '/etc/hyperledger/fabric/ca/ca-key.pem'
        },
        'port': {
            'internal': 7054,
            'external': 8054
        },
        'url': 'https://rca-chu-nantes:7054',
        'logfile': '/substra/data/log/rca-chu-nantes.log',
        'server-config-path': '/substra/conf/chu-nantes/fabric-ca-server-config.yaml',
        'client-config-path': '/substra/conf/chu-nantes/fabric-ca-client-config.yaml',
        'affiliations': {
            'chu-nantes': ['nantes']
        },
        'users': {
            'bootstrap_admin': bootstrap_admin,
        },
    },
    'users': {
        'admin': admin,
        'user': user,
    },
    'csr': {
        'cn': 'rca-chu-nantes',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-chu-nantes'],
        'names': [
            {'C': 'FR',
             'ST': 'Loire-Atlantique',
             'L': 'Nantes',
             'O': 'chu-nantes',
             'OU': None}
        ],
    },
    'core_dir': {
        'internal': '/etc/hyperledger/fabric',
    },
    'peers': [peer1, peer2]
}

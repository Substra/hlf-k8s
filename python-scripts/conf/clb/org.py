from .peers.peer1 import peer1
from .peers.peer2 import peer2
from .users.admin import admin
from .users.bootstrap_admin import bootstrap_admin
from .users.user import user

clb = {
    'name': 'clb',
    'msp_id': 'clbMSP',
    'anchor_tx_file': '/substra/data/orgs/clb/anchors.tx',
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in
        # the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
        'certfile': '/substra/data/orgs/clb/tls-ca-cert.pem',
        'clientkey': ''
    },
    'ca': {
        'name': 'rca-clb',
        'host': 'rca-clb',
        'certfile': '/substra/data/orgs/clb/ca-cert.pem',
        'keyfile': '/substra/data/orgs/clb/ca-key.pem',
        'port': {
            'internal': 7054,
            'external': 10054
        },
        'url': 'https://rca-clb:7054',
        'logfile': '/substra/data/log/rca-clb.log',
        'server-config-path': '/substra/conf/clb/fabric-ca-server-config.yaml',
        'client-config-path': '/substra/conf/clb/fabric-ca-client-config.yaml',
        'affiliations': {
            'clb': ['lyon']
        }
    },
    'users': {
        'bootstrap_admin': bootstrap_admin,
        'admin': admin,
        'user': user,
    },
    'csr': {
        'cn': 'rca-clb',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-clb'],
        'names': [
            {'C': 'FR',
             'ST': 'Rhone',
             'L': 'Lyon',
             'O': 'clb',
             'OU': None}
        ],
    },
    'core_dir': {
        'internal': '/etc/hyperledger/fabric',
    },
    'peers': [peer1, peer2]
}

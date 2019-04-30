from .peers.peer1 import peer1
from .peers.peer2 import peer2
from .users.admin import admin
from .users.bootstrap_admin import bootstrap_admin
from .users.user import user

owkin = {
    'name': 'owkin',
    'msp_id': 'owkinMSP',
    'anchor_tx_file': '/substra/data/orgs/owkin/anchors.tx',
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
        'certfile': '/substra/data/orgs/owkin/tls-ca-cert.pem',
        'clientkey': ''
    },
    'ca': {
        'name': 'rca-owkin',
        'host': 'rca-owkin',
        'certfile': '/substra/data/orgs/owkin/ca-cert.pem',
        'keyfile': '/substra/data/orgs/owkin/ca-key.pem',
        'port': {
            'internal': 7054,
            'external': 7054
        },
        'url': 'https://rca-owkin:7054',
        'logfile': '/substra/data/log/rca-owkin.log',
        'server-config-path': '/substra/conf/owkin/fabric-ca-server-config.yaml',
        'client-config-path': '/substra/conf/owkin/fabric-ca-client-config.yaml',
    },
    'users': {
        'bootstrap_admin': bootstrap_admin,
        'admin': admin,
        'user': user,
    },
    'csr': {
        'cn': 'rca-owkin',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-owkin']
    },
    'core': {
        'docker': {
            'peer_home': '/etc/hyperledger/fabric',
            'msp_config_path': '/etc/hyperledger/fabric/msp',
        },
        'host': {
            'peer_home': '/substra/data/orgs/owkin',
            'msp_config_path': '/substra/data/orgs/owkin/user/msp',
        }
    },
    'peers': [peer1, peer2]
}

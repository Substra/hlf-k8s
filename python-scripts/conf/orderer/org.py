from .users.bootstrap_admin import bootstrap_admin
from .users.admin import admin
from orderer.orderers.orderer1 import orderer1

orderer = {
    'name': 'orderer',
    'msp_id': 'ordererMSP',
    'broadcast_dir': '/substra/data/log/broadcast',
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a
        # example file with this name is already present in the docker
        # image, do not forget to remove these examples files in your
        # docker CMD overriding if naming the same way
        'certfile': '/substra/data/orgs/orderer/tls-ca-cert.pem',
        'clientkey': ''
    },
    'ca': {
        'name': 'rca-orderer',
        'host': 'rca-orderer',
        'certfile': '/substra/data/orgs/orderer/ca-cert.pem',
        'keyfile': '/substra/data/orgs/orderer/ca-key.pem',
        'port': {
            'internal': 7054,
            'external': 9054
        },
        'url': 'https://rca-orderer:7054',
        'logfile': '/substra/data/log/rca-orderer.log',
        'server-config-path': '/substra/conf/orderer/fabric-ca-server-config.yaml',
        'client-config-path': '/substra/conf/orderer/fabric-ca-client-config.yaml',
    },
    'users': {
        'bootstrap_admin': bootstrap_admin,
        'admin': admin,
    },
    'csr': {
        'cn': 'rca-orderer',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-orderer']
    },
    'core_dir': {
        'internal': '/etc/hyperledger/fabric',
    },
    'orderers': [orderer1],
}

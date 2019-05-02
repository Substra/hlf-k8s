from .users.bootstrap_admin import bootstrap_admin
from .users.admin import admin
from orderer.orderers.orderer1 import orderer1

orderer = {
    'host': 'orderer1-orderer',
    'port': {
        'internal': 7050,
        'external': 7050
    },
    'name': 'orderer',
    'msp_id': 'ordererMSP',
    'broadcast_dir': '/substra/data/log/broadcast',
    'home': '/etc/hyperledger/fabric',
    'config-path': '/substra/conf/orderer/orderer.yaml',
    'core': {
        'docker': '/etc/hyperledger/fabric/',
        'host': '/substra/data/orgs/orderer',
    },
    'core_dir': {
        'internal': '/etc/hyperledger/fabric',
        'external': '/substra/data/orgs/orderer'
    },
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a
        # example file with this name is already present in the docker
        # image, do not forget to remove these examples files in your
        # docker CMD overriding if naming the same way
        'certfile': '/substra/data/orgs/orderer/tls-ca-cert.pem',
        'key': '/substra/data/orgs/orderer/tls/server.key',
        'cert': '/substra/data/orgs/orderer/tls/server.crt',
        # will be the same as certfile normally, used for explicitely
        # decoupling cert INSIDE container
        'ca': 'ca.pem',
        'dir': '/substra/data/orgs/orderer/tls/',
        'clientCert': '/substra/data/orgs/orderer/tls/cli-client.crt',
        'clientKey': '/substra/data/orgs/orderer/tls/cli-client.key',
        'clientCa': '/substra/data/orgs/orderer/tls/cli-client.pem',

        'core_dir': {
            'external': '/substra/data/orgs/orderer/tls/orderer1',
            'internal': '/etc/hyperledger/fabric/tls'
        },
        'client': {
            'dir': 'client',
            'cert': 'client.crt',
            'key': 'client.key',
            'ca': 'client.pem'
        },
        'server': {
            'dir': 'server',
            'cert': 'server.crt',
            'key': 'server.key',
            'ca': 'server.pem'
        },
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
        'orderer': {
            'name': 'orderer',
            'pass': 'ordererpw',
            'home': '/substra/data/orgs/orderer/orderer'
        }
    },
    'csr': {
        'cn': 'rca-orderer',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-orderer']
    },
    'orderers': [orderer1],
}

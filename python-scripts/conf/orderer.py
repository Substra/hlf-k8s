orderer = {
    'host': 'orderer1-orderer',
    'port': 7050,
    'name': 'orderer',
    'msp_dir': '/substra/data/orgs/orderer/msp',
    'msp_id': 'ordererMSP',
    'admin_home': '/substra/data/orgs/orderer/admin',
    'broadcast_dir': '/substra/data/log/broadcast',
    'home': '/etc/hyperledger/fabric',
    'local_msp_dir': '/etc/hyperledger/fabric/msp',
    'ca-server-config-path': '/substra/conf/orderer/fabric-ca-server-config.yaml',
    'ca-client-config-path': '/substra/conf/orderer/fabric-ca-client-config.yaml',
    'config-path': '/substra/conf/orderer/orderer.yaml',
    'core': {
        'docker': '/etc/hyperledger/fabric/',
        'host': '/substra/data/orgs/orderer',
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
    },
    'ca': {
        'name': 'rca-orderer',
        'host': 'rca-orderer',
        'certfile': '/substra/data/orgs/orderer/ca-cert.pem',
        'keyfile': '/substra/data/orgs/orderer/ca-key.pem',
        'port': 7054,
        'host_port': 9054,
        'url': 'https://rca-orderer:7054',
        'logfile': '/substra/data/log/rca-orderer.log',
    },
    'users': {
        'bootstrap_admin': {
            'name': 'admin',
            'pass': 'adminpw',
            'home': '/substra/data/orgs/orderer'
        },
        'admin': {
            'name': 'admin-orderer',
            'pass': 'admin-ordererpw',
            'home': '/substra/data/orgs/orderer/admin'
        },
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
}

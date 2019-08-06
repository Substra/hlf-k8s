import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

orderer1 = {
    'name': 'orderer1-orderer',
    'pass': 'ordererpw',
    'host': 'orderer1-orderer',
    'port': {
        'internal': 7050,
        'external': 7050
    },
    'operations': {
        'prometheus': {
            'port': {
                'internal': 8443,
                'external': 8443
            }
        },
        'statsd': {
            'port': {
                'internal': 8125,
                'external': 7125
            }
        },
    },
    'tls': {
        'dir': {
            'external': f'{SUBSTRA_PATH}/data/orgs/orderer/tls/orderer1',
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
    }
}

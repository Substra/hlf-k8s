import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

peer2 = {
    'name': 'peer2-clb',
    'pass': 'peer2pw',
    'host': 'peer2-clb',
    'port': {
        'internal': 7051,
        'external': 12051
    },
    'operations': {
        'prometheus': {
            'port': {
                'internal': 9443,
                'external': 14443
            }
        },
        'statsd': {
            'port': {
                'internal': 8125,
                'external': 13125
            }
        },
    },
    'anchor': False,
    'tls': {
        'dir': {
            'external': f'{SUBSTRA_PATH}/data/orgs/clb/tls/peer2',
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
            #  paradoxically, this will not be a tls certificate,
            #  but will be put by fabric-ca inside tlscacerts directory
            # it will be equal to org['ca']['certfile']
            'ca': 'server.pem'
        },
    }
}

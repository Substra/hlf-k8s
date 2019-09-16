import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

peer1 = {
    'name': 'peer1-chu-nantes',
    'pass': 'peer1pw',
    'host': 'peer1-chu-nantes',
    'port': {
        'internal': 7051,
        'external': 9051
    },
    'operations': {
        'prometheus': {
            'port': {
                'internal': 9443,
                'external': 11443
            }
        },
        'statsd': {
            'port': {
                'internal': 8125,
                'external': 10125
            }
        },
    },
    'anchor': True,
    'tls': {
        'dir': {
            'external': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/tls/peer1',
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

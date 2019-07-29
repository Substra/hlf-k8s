import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

peer1 = {
    'name': 'peer1-clb',
    'pass': 'peer1pw',
    'host': 'peer1-clb',
    'port': {
        'internal': 7051,
        'external': 11051
    },
    'anchor': True,
    'tls': {
        'dir': {
            'external': f'{SUBSTRA_PATH}/data/orgs/clb/tls/peer1',
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

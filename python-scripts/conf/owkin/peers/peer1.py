peer1 = {
    'name': 'peer1',
    'pass': 'peer1pw',
    'host': 'peer1-owkin',
    'port': {
        'internal': 7051,
        'external': 7051
    },
    'anchor': True,
    'tls': {
        'dir': {
            'external': '/substra/data/orgs/owkin/tls/peer1',
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

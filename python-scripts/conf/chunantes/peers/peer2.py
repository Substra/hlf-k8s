peer2 = {
    'name': 'peer2-chu-nantes',
    'pass': 'peer2pw',
    'host': 'peer2-chu-nantes',
    'port': {
        'internal': 7051,
        'external': 10051
    },
    'anchor': False,
    'tls': {
        'dir': {
            'external': '/substra/data/orgs/chu-nantes/tls/peer2',
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

peer1 = {
    'name': 'peer1-orderer',
    'pass': 'peer1pw',
    'host': 'peer1-orderer',
    'port': {
        'internal': 7051,
        'external': 11051
    },
    'anchor': True,
    'tls': {
        'dir': {
            'external': '/substra/data/orgs/orderer/tls/peer1',
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

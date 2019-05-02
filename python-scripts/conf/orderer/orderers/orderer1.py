orderer1 = {
    'name': 'orderer1',
    'pass': 'ordererpw',
    'host': 'orderer1-orderer',
    'home': '/substra/data/orgs/orderer/orderer1',
    'port': {
        'internal': 7050,
        'external': 7050
    },
    'tls': {
        'dir': {
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
    }
}

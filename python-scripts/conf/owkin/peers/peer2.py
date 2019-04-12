peer2 = {
    'name': 'peer2',
    'pass': 'peer2pw',
    'host': 'peer2-owkin',
    'port': 7051,
    'host_port': 8051,
    'event_port': 7053,
    'host_event_port': 8053,
    'anchor': False,
    'docker_core_dir': '/substra/conf/owkin/peer2',
    'tls': {
        'dir': '/substra/data/orgs/owkin/tls/peer2/',
        'clientCert': '/substra/data/orgs/owkin/tls/peer2/cli-client.crt',
        'clientKey': '/substra/data/orgs/owkin/tls/peer2/cli-client.key',
        'clientCa': '/substra/data/orgs/owkin/tls/peer2/cli-client.pem',
        'serverCert': '/substra/data/orgs/owkin/tls/peer2/server.crt',
        'serverKey': '/substra/data/orgs/owkin/tls/peer2/server.key',
        #  paradoxically, this will not be a tls certificate,
        #  but will be put by fabric-ca inside tlscacerts directory
        # it will be equal to org['ca']['certfile']
        'serverCa': '/substra/data/orgs/owkin/tls/peer2/server.pem',
    }
}

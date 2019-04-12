peer1 = {
    'name': 'peer1',
    'pass': 'peer1pw',
    'host': 'peer1-chu-nantes',
    'port': 7051,
    'host_port': 9051,
    'event_port': 7053,
    'host_event_port': 9053,
    'anchor': True,
    'docker_core_dir': '/substra/conf/chu-nantes/peer1',
    'tls': {
        'dir': '/substra/data/orgs/chu-nantes/tls/peer1/',
        'clientCert': '/substra/data/orgs/chu-nantes/tls/peer1/cli-client.crt',
        'clientKey': '/substra/data/orgs/chu-nantes/tls/peer1/cli-client.key',
        'clientCa': '/substra/data/orgs/chu-nantes/tls/peer1/cli-client.pem',
        'serverCert': '/substra/data/orgs/chu-nantes/tls/peer1/server.crt',
        'serverKey': '/substra/data/orgs/chu-nantes/tls/peer1/server.key',
        #  paradoxically, this will not be a tls certificate,
        #  but will be put by fabric-ca inside tlscacerts directory
        # it will be equal to org['ca']['certfile']
        'serverCa': '/substra/data/orgs/chu-nantes/tls/peer1/server.pem',
    }
}

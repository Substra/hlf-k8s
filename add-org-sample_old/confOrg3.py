conf = {
    'orgs': {
        'org3': {
            'org_name': 'org3',
            'org_msp_dir': '/data/orgs/org3/msp',
            'org_msp_id': 'org3MSP',
            'admin_home': '/data/orgs/org3/admin',
            'user_home': '/data/orgs/org3/user',
            'anchor_tx_file': '/data/orgs/org3/anchors.tx',
            'tls': {
                # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
                'certfile': '/data/orgs/org3/ca-cert.pem',
                'clientkey': ''
            },
            'ca': {
                'name': 'rca-org3',
                'host': 'rca-org3',
                'certfile': 'ca-cert.pem',
                'port': 7054,
                'url': 'https://rca-org3:7054',
                'logfile': 'data/logs/rca-org3.log'
            },
            'users': {
                'bootstrap_admin': {
                    'name': 'admin',
                    'pass': 'adminpw'
                },
                'admin': {
                    'name': 'admin-org3',
                    'pass': 'admin-org3pw'
                },
                'user': {
                    'name': 'user-org3',
                    'pass': 'user-org3pw'
                },
            },
            'csr': {
                'cn': 'rca-org3',
                # The "hosts" value is a list of the domain names which the certificate should be valid for.
                'hosts': ['rca-org3']
            },
            'core': {
                'peer_home': '/opt/gopath/src/github.com/hyperledger/fabric/peer',
                'msp_config_path': '/opt/gopath/src/github.com/hyperledger/fabric/peer/msp',
                'tls': {
                    'key': 'server.key',
                    'cert': 'server.crt'
                }
            },
            'peers': [
                {
                    'name': 'peer1',
                    'pass': 'peer1pw',
                    'host': 'peer1-org3',
                    'port': 7051
                },
                {
                    'name': 'peer2',
                    'pass': 'peer2pw',
                    'host': 'peer2-org3',
                    'port': 7051
                }
            ]
        },
    },
    'orderer': {},

    'misc': {
        'genesis_bloc_file': '/data/genesis.block',
        'channel_tx_file': '/data/channel.tx',
        'channel_name': 'mychannel',
        'chaincode_name': 'mycc',
        'config_block_file': '/tmp/config_block.pb',
        'config_update_envelope_file': '/tmp/config_update_as_envelope.pb',
        'setup_logfile': '/data/logs/setupOrg3.log',
        'setup_success_file': '/data/logs/setupOrg3.successful',
        'run_logfile': '/data/logs/runOrg3.log',
        'run_sumfile': '/data/logs/runOrg3.sum',
        'run_success_file': '/data/logs/runOrg3.successful',
        'run_fail_file': '/data/logs/runOrg3.fail'
    }
}

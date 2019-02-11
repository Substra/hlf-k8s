import json

conf = {
    'orgs': [
        {
            'name': 'owkin',
            'msp_dir': '/substra/data/orgs/owkin/msp',
            'msp_id': 'owkinMSP',
            'user_home': '/substra/data/orgs/owkin/user',
            'anchor_tx_file': '/substra/data/orgs/owkin/anchors.tx',
            'ca-server-config-path': '/substra/conf/owkin/fabric-ca-server-config.yaml',
            'ca-client-config-path': '/substra/conf/owkin/fabric-ca-client-config.yaml',
            'tls': {
                # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
                'certfile': '/substra/data/orgs/owkin/tls-ca-cert.pem',
                'clientkey': ''
            },
            'ca': {
                'name': 'rca-owkin',
                'host': 'rca-owkin',
                'certfile': '/substra/data/orgs/owkin/ca-cert.pem',
                'keyfile': '/substra/data/orgs/owkin/ca-key.pem',
                'port': 7054,
                'host_port': 7054,
                'url': 'https://rca-owkin:7054',
                'logfile': '/substra/data/logs/rca-owkin.log'
            },
            'users': {
                'bootstrap_admin': {
                    'name': 'admin',
                    'pass': 'adminpw',
                    'home': '/substra/data/orgs/owkin'
                },
                'admin': {
                    'name': 'admin-owkin',
                    'pass': 'admin-owkinpw',
                    'home': '/substra/data/orgs/owkin/admin'
                },
                'user': {
                    'name': 'user-owkin',
                    'pass': 'user-owkinpw',
                    'home': '/substra/data/orgs/owkin/user'
                },
            },
            'csr': {
                'cn': 'rca-owkin',
                # The "hosts" value is a list of the domain names which the certificate should be valid for.
                'hosts': ['rca-owkin']
            },
            'core': {
                'docker': {
                    'peer_home': '/etc/hyperledger/fabric',
                    'msp_config_path': '/etc/hyperledger/fabric/msp',
                },
                'host': {
                    'peer_home': '/substra/data/orgs/owkin',
                    'msp_config_path': '/substra/data/orgs/owkin/user/msp',
                }
            },
            'peers': [
                {
                    'name': 'peer1',
                    'pass': 'peer1pw',
                    'host': 'peer1-owkin',
                    'port': 7051,
                    'host_port': 7051,
                    'event_port': 7053,
                    'host_event_port': 7053,
                    'anchor': True,
                    'docker_core_dir': '/substra/conf/owkin/peer1',
                    'host_core_dir': '/substra/conf/owkin/peer1-host',
                    'tls': {
                        'dir': '/substra/data/orgs/owkin/tls/peer1/',
                        'clientCert': '/substra/data/orgs/owkin/tls/peer1/cli-client.crt',
                        'clientKey': '/substra/data/orgs/owkin/tls/peer1/cli-client.key',
                        'clientCa': '/substra/data/orgs/owkin/tls/peer1/cli-client.pem',
                        'serverCert': '/etc/hyperledger/fabric/tls/server.crt',
                        'serverKey': '/etc/hyperledger/fabric/tls/server.key',
                        #  paradoxically, this will not be a tls certificate,
                        #  but will be put by fabric-ca inside tlscacerts directory
                        # it will be equal to org['ca']['certfile']
                        'serverCa': '/substra/data/orgs/owkin/tls/peer1/server.pem',
                    }
                },
                {
                    'name': 'peer2',
                    'pass': 'peer2pw',
                    'host': 'peer2-owkin',
                    'port': 7051,
                    'host_port': 8051,
                    'event_port': 7053,
                    'host_event_port': 8053,
                    'anchor': False,
                    'docker_core_dir': '/substra/conf/owkin/peer2',
                    'host_core_dir': '/substra/conf/owkin/peer2-host',
                    'tls': {
                        'dir': '/substra/data/orgs/owkin/tls/peer2/',
                        'clientCert': '/substra/data/orgs/owkin/tls/peer2/cli-client.crt',
                        'clientKey': '/substra/data/orgs/owkin/tls/peer2/cli-client.key',
                        'clientCa': '/substra/data/orgs/owkin/tls/peer2/cli-client.pem',
                        'serverCert': '/etc/hyperledger/fabric/tls/server.crt',
                        'serverKey': '/etc/hyperledger/fabric/tls/server.key',
                        #  paradoxically, this will not be a tls certificate,
                        #  but will be put by fabric-ca inside tlscacerts directory
                        # it will be equal to org['ca']['certfile']
                        'serverCa': '/substra/data/orgs/owkin/tls/peer2/server.pem',
                    }
                }
            ]
        }
    ],
    'orderers': [
        {
            'host': 'orderer1-orderer',
            'port': 7050,
            'name': 'orderer',
            'msp_dir': '/substra/data/orgs/orderer/msp',
            'msp_id': 'ordererMSP',
            'admin_home': '/substra/data/orgs/orderer/admin',
            'broadcast_dir': '/substra/data/logs/broadcast',
            'home': '/etc/hyperledger/fabric',
            'local_msp_dir': '/etc/hyperledger/fabric/msp',
            'ca-server-config-path': '/substra/conf/orderer/fabric-ca-server-config.yaml',
            'ca-client-config-path': '/substra/conf/orderer/fabric-ca-client-config.yaml',
            'config-path': '/substra/conf/orderer/orderer.yaml',
            'tls': {
                # careful, `ca-cert.pem` is the default cert name file and a
                # example file with this name is already present in the docker
                # image, do not forget to remove these examples files in your
                # docker CMD overriding if naming the same way
                'certfile': '/substra/data/orgs/orderer/tls-ca-cert.pem',
                'key': 'server.key',
                'cert': 'server.crt',
                # will be the same as certfile normally, used for explicitely
                # decoupling cert INSIDE container
                'ca': 'ca.pem',
            },
            'ca': {
                'name': 'rca-orderer',
                'host': 'rca-orderer',
                'certfile': '/substra/data/orgs/orderer/ca-cert.pem',
                'keyfile': '/substra/data/orgs/orderer/ca-key.pem',
                'port': 7054,
                'host_port': 9054,
                'url': 'https://rca-orderer:7054',
                'logfile': '/substra/data/logs/rca-orderer.log',
            },
            'users': {
                'bootstrap_admin': {
                    'name': 'admin',
                    'pass': 'adminpw',
                    'home': '/substra/data/orgs/orderer'
                },
                'admin': {
                    'name': 'admin-orderer',
                    'pass': 'admin-ordererpw',
                    'home': '/substra/data/orgs/orderer/admin'
                },
                'orderer': {
                    'name': 'orderer',
                    'pass': 'ordererpw',
                    'home': '/substra/data/orgs/orderer/orderer'
                }
            },
            'csr': {
                'cn': 'rca-orderer',
                # The "hosts" value is a list of the domain names which the certificate should be valid for.
                'hosts': ['rca-orderer']
            },
        }
    ],
    'misc': {
        'channel_name': 'mychannel',
        'channel_block': '/substra/data/mychannel.block',
        'chaincode_name': 'mycc',
        'genesis_bloc_file': '/substra/data/genesis.block',
        'channel_tx_file': '/substra/data/channel.tx',
        'configtx-config-path': '/substra/data/configtx.yaml',
        'config_block_file': '/tmp/config_block.pb',
        'config_update_envelope_file': '/tmp/config_update_as_envelope.pb',

        'setup_logfile': '/substra/data/logs/setup.log',
        'setup_success_file': '/substra/data/logs/setup.successful',

        'run_logfile': '/substra/data/logs/run.log',
        'run_sumfile': '/substra/data/logs/run.sum',
        'run_success_file': '/substra/data/logs/run.successful',
        'run_fail_file': '/substra/data/logs/run.fail',

        'fixtures_logfile': '/substra/data/logs/fixtures.log',
        'fixtures_success_file': '/substra/data/logs/fixtures.successful',
        'fixtures_fail_file': '/substra/data/logs/fixtures.fail',

        'revoke_logfile': '/substra/data/logs/revoke.log',
        'revoke_success_file': '/substra/data/logs/revoke.successful',
        'revoke_fail_file': '/substra/data/logs/revoke.fail',

        'fixtures_path': 'fixtures2orgs.py'
    }
}

if __name__ == '__main__':
    with open('/substra/conf/conf.json', 'w+') as write_file:
        json.dump(conf, write_file, indent=True)

import json

conf = {
    'orgs': {
        'owkin': {
            'org_name': 'owkin',
            'org_msp_dir': '/substra/data/orgs/owkin/msp',
            'org_msp_id': 'owkinMSP',
            'admin_home': '/substra/data/orgs/owkin/admin',
            'user_home': '/substra/data/orgs/owkin/user',
            'anchor_tx_file': '/substra/data/orgs/owkin/anchors.tx',
            'tls': {
                # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
                'certfile': '/substra/data/orgs/owkin/ca-cert.pem',
                'clientkey': ''
            },
            'ca': {
                'name': 'rca-owkin',
                'host': 'rca-owkin',
                'certfile': 'ca-cert.pem',
                'port': 7054,
                'host_port': 7054,
                'url': 'https://rca-owkin:7054',
                'logfile': 'data/logs/rca-owkin.log'
            },
            'users': {
                'bootstrap_admin': {
                    'name': 'admin',
                    'pass': 'adminpw'
                },
                'admin': {
                    'name': 'admin-owkin',
                    'pass': 'admin-owkinpw'
                },
                'user': {
                    'name': 'user-owkin',
                    'pass': 'user-owkinpw'
                },
            },
            'csr': {
                'cn': 'rca-owkin',
                # The "hosts" value is a list of the domain names which the certificate should be valid for.
                'hosts': ['rca-owkin']
            },
            'core': {
                'docker': {
                    'peer_home': '/opt/gopath/src/github.com/hyperledger/fabric/peer',
                    'msp_config_path': '/opt/gopath/src/github.com/hyperledger/fabric/peer/msp',
                },
                'host': {
                    'peer_home': '/substra/data/orgs/owkin',
                    'msp_config_path': '/substra/data/orgs/owkin/user/msp',
                },
                'tls': {
                    'key': 'server.key',
                    'cert': 'server.crt'
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
                },
                {
                    'name': 'peer2',
                    'pass': 'peer2pw',
                    'host': 'peer2-owkin',
                    'port': 7051,
                    'host_port': 8051,
                    'event_port': 7053,
                    'host_event_port': 8053,
                }
            ]
        },
        'chu-nantes': {
            'org_name': 'chu-nantes',
            'org_msp_dir': '/substra/data/orgs/chu-nantes/msp',
            'org_msp_id': 'chu-nantesMSP',
            'admin_home': '/substra/data/orgs/chu-nantes/admin',
            'user_home': '/substra/data/orgs/chu-nantes/user',
            'anchor_tx_file': '/substra/data/orgs/chu-nantes/anchors.tx',
            'tls': {
                # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in the docker image, do not forget to remove these examples files if naming the same way
                'certfile': '/substra/data/orgs/chu-nantes/ca-cert.pem',
                'clientkey': ''
            },
            'ca': {
                'name': 'rca-chu-nantes',
                'host': 'rca-chu-nantes',
                'certfile': 'ca-cert.pem',
                'port': 7054,
                'host_port': 8054,
                'url': 'https://rca-chu-nantes:7054',
                'logfile': 'data/logs/rca-chu-nantes.log'
            },
            'users': {
                'bootstrap_admin': {
                    'name': 'admin',
                    'pass': 'adminpw'
                },
                'admin': {
                    'name': 'admin-chu-nantes',
                    'pass': 'admin-chu-nantespw'
                },
                'user': {
                    'name': 'user-chu-nantes',
                    'pass': 'user-chu-nantespw'
                },
            },
            'csr': {
                'cn': 'rca-chu-nantes',
                # The "hosts" value is a list of the domain names which the certificate should be valid for.
                'hosts': ['rca-chu-nantes']
            },
            'core': {
                'docker': {
                    'peer_home': '/opt/gopath/src/github.com/hyperledger/fabric/peer',
                    'msp_config_path': '/opt/gopath/src/github.com/hyperledger/fabric/peer/msp',
                },
                'host': {
                    'peer_home': '/substra/data/orgs/chu-nantes',
                    'msp_config_path': '/substra/data/orgs/chu-nantes/user/msp',
                },
                'tls': {
                    'key': 'server.key',
                    'cert': 'server.crt'
                }
            },
            'peers': [
                {
                    'name': 'peer1',
                    'pass': 'peer1pw',
                    'host': 'peer1-chu-nantes',
                    'port': 7051,
                    'host_port': 9051,
                    'event_port': 7053,
                    'host_event_port': 9053,
                },
                {
                    'name': 'peer2',
                    'pass': 'peer2pw',
                    'host': 'peer2-chu-nantes',
                    'port': 7051,
                    'host_port': 10051,
                    'event_port': 7053,
                    'host_event_port': 10053,
                }
            ]
        },
    },
    'orderers': {
        'orderer': {
            'host': 'orderer1-orderer',
            'port': 7050,
            'org_name': 'orderer',
            'org_msp_dir': '/substra/data/orgs/orderer/msp',
            'org_msp_id': 'ordererMSP',
            'admin_home': '/substra/data/orgs/orderer/admin',
            'broadcast_dir': '/substra/data/logs/broadcast',
            'home': '/etc/hyperledger/orderer',
            'local_msp_dir': '/etc/hyperledger/orderer/msp',
            'tls': {
                # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
                'certfile': '/substra/data/orgs/orderer/ca-cert.pem',
                'key': 'server.key',
                'cert': 'server.crt',
            },
            'ca': {
                'name': 'rca-orderer',
                'host': 'rca-orderer',
                'certfile': 'ca-cert.pem',
                'port': 7054,
                'host_port': 9054,
                'url': 'https://rca-orderer:7054',
                'logfile': 'data/logs/rca-orderer.log',
            },
            'users': {
                'bootstrap_admin': {
                    'name': 'admin',
                    'pass': 'adminpw'
                },
                'admin': {
                    'name': 'admin-orderer',
                    'pass': 'admin-ordererpw'
                },
                'orderer': {
                    'name': 'orderer',
                    'pass': 'ordererpw'
                }
            },
            'csr': {
                'cn': 'rca-orderer',
                # The "hosts" value is a list of the domain names which the certificate should be valid for.
                'hosts': ['rca-orderer']
            },
        }
    },
    'misc': {
        'genesis_bloc_file': '/substra/data/genesis.block',
        'channel_tx_file': '/substra/data/channel.tx',
        'channel_name': 'mychannel',
        'chaincode_name': 'mycc',
        'config_block_file': '/tmp/config_block.pb',
        'config_update_envelope_file': '/tmp/config_update_as_envelope.pb',
        'setup_logfile': '/substra/data/logs/setup.log',
        'setup_success_file': '/substra/data/logs/setup.successful',
        'run_logfile': '/substra/data/logs/run.log',
        'run_sumfile': '/substra/data/logs/run.sum',
        'run_success_file': '/substra/data/logs/run.successful',
        'run_fail_file': '/substra/data/logs/run.fail'
    }
}

if __name__ == '__main__':
    with open('/substra/conf/conf.json', 'w+') as write_file:
        json.dump(conf, write_file, indent=True)

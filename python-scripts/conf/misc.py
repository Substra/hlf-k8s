import os


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

misc = {
    'system_channel_name': 'substrasystemchannel',
    'system_channel_block': 'systemchannel.block',

    'channel_name': 'substrachannel',
    'channel_block': f'{SUBSTRA_PATH}/data/channel/substrachannel.block',
    'channel_tx_file': f'{SUBSTRA_PATH}/data/channel/substrachannel.tx',

    'chaincode_name': 'substracc',
    'chaincode_version': '1.0',
    'chaincode_path': 'chaincode/',

    'genesis_bloc_file': {
        'external': f'{SUBSTRA_PATH}/data/genesis/genesis.block',
        'internal': '/etc/hyperledger/fabric/genesis/genesis.block'
    },

    'config_block_file': '/tmp/config_block.pb',
    'config_update_envelope_file': '/tmp/config_update_as_envelope.pb',
}

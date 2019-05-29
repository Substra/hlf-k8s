misc = {
    'system_channel_name': 'substrasystemchannel',
    'system_channel_block': 'systemchannel.block',

    'channel_name': 'substrachannel',
    'channel_block': '/substra/data/channel/substrachannel.block',
    'channel_tx_file': '/substra/data/channel/substrachannel.tx',

    'chaincode_name': 'substracc',
    'chaincode_version': '1.0',
    'chaincode_path': 'github.com/hyperledger/chaincode/',

    'genesis_bloc_file': {
        'external': '/substra/data/genesis/genesis.block',
        'internal': '/etc/hyperledger/fabric/genesis/genesis.block'
    },

    'config_block_file': '/tmp/config_block.pb',
    'config_update_envelope_file': '/tmp/config_update_as_envelope.pb',
}

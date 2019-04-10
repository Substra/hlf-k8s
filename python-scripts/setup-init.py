import json
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call

from setup import registerOrdererIdentities, registerUsers


def generateChannelArtifacts(conf):
    print('Generating orderer genesis block at %(genesis_bloc_file)s' % {
        'genesis_bloc_file': conf['misc']['genesis_bloc_file']
    }, flush=True)

    # Note: For some unknown reason (at least for now) the block file can't be
    # named orderer.genesis.block or the orderer will fail to launch

    # configtxgen -profile OrgsOrdererGenesis -outputBlock /substra/data/genesis.block
    call(['configtxgen',
          '-profile', 'OrgsOrdererGenesis',
          '-channelID', 'substrasystemchannel',
          '-outputBlock', conf['misc']['genesis_bloc_file']])

    # print('Generating channel configuration transaction at %(channel_tx_file)s' % {
    #     'channel_tx_file': conf['misc']['channel_tx_file']}, flush=True)

    # call(['configtxgen',
    #       '-profile', 'OrgsChannel',
    #       '-outputCreateChannelTx', conf['misc']['channel_tx_file'],
    #       '-channelID', conf['misc']['channel_name']])

    # for org in conf['orgs']:
    #     print('Generating anchor peer update transaction for %(org_name)s at %(anchor_tx_file)s' % {
    #         'org_name': org['name'],
    #         'anchor_tx_file': org['anchor_tx_file']
    #     }, flush=True)

    #     call(['configtxgen',
    #           '-profile', 'OrgsChannel',
    #           '-outputAnchorPeersUpdate', org['anchor_tx_file'],
    #           '-channelID', conf['misc']['channel_name'],
    #           '-asOrg', org['name']])


if __name__ == '__main__':

    conf_path = '/substra/conf/conf.json'
    conf = json.load(open(conf_path, 'r'))

    registerOrdererIdentities(conf)
    conf['orgs'] = []  # Hack for setup
    registerUsers(conf)
    generateChannelArtifacts(conf)
    print('Finished building channel artifacts', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

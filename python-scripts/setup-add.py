import json
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call

from util import completeMSPSetup
from setup import configLocalMSP, registerPeerIdentities


def registerIdentities(conf):
    print('Registering identities...\n', flush=True)

    registerPeerIdentities(conf)


def registerUsers(conf):
    print('Getting CA certificates ...\n', flush=True)

    for org in conf['orgs']:
        org_admin_msp_dir = org['users']['admin']['home'] + '/msp'

        # will create admin and user folder with an msp folder and populate it. Populate admincerts for configtxgen to work
        # https://hyperledger-fabric.readthedocs.io/en/release-1.2/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp

        # register admin and create admincerts
        configLocalMSP(org, 'admin')
        # needed for tls communication for create channel from peer for example, copy tlscacerts from cacerts
        completeMSPSetup(org_admin_msp_dir)

        # register user and create admincerts
        configLocalMSP(org, 'user')


def generateChannelArtifacts(conf):
    for org in conf['orgs']:
        print('Generating anchor peer update transaction for %(org_name)s at %(anchor_tx_file)s' % {
            'org_name': org['name'],
            'anchor_tx_file': org['anchor_tx_file']
        }, flush=True)

        call(['configtxgen',
              '-profile', 'OrgsChannel',
              '-outputAnchorPeersUpdate', org['anchor_tx_file'],
              '-channelID', conf['misc']['channel_name'],
              '-asOrg', org['name']])


def generateChannelUpdate():

    call(['sh', '/scripts/add-org.sh'])


if __name__ == '__main__':

    conf_path = '/substra/conf/conf-add.json'
    conf = json.load(open(conf_path, 'r'))

    conf['orderers'] = []  # Hack for setup
    registerIdentities(conf)
    registerUsers(conf)
    generateChannelArtifacts(conf)
    generateChannelUpdate()

    print('Finished building channel artifacts', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

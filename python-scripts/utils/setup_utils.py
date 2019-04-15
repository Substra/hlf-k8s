import os
from subprocess import call
from shutil import copytree

from .common_utils import waitPort, completeMSPSetup, dowait


def configLocalMSP(org, user_name):
    user = org['users'][user_name]
    org_user_home = user['home']
    org_user_msp_dir = org_user_home + '/msp'

    # if local admin msp does not exist, create it by enrolling user
    if not os.path.exists(org_user_msp_dir):
        print('Enroll user and copy in admincert for configtxgen', flush=True)

        # wait ca certfile exists before enrolling
        dowait('%(ca_name)s to start' % {'ca_name': org['ca']['name']},
               90,
               org['ca']['logfile'],
               [org['ca']['certfile']])

        msg = 'Enrolling user \'%(user_name)s\' for organization %(org)s with %(ca_host)s and home directory %(org_user_home)s...'
        print(msg % {
            'user_name': user['name'],
            'org': org['name'],
            'ca_host': org['ca']['host'],
            'org_user_home': org_user_home
        }, flush=True)

        enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
            'name': user['name'],
            'pass': user['pass'],
            'host': org['ca']['host'],
            'port': org['ca']['port']
        }

        call(['fabric-ca-client',
              'enroll', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '-u', enrollment_url,
              '-M', org_user_msp_dir])  # :warning: override msp dir

        # admincerts is required for configtxgen binary
        # will copy cert.pem from <user>/msp/signcerts to <user>/msp/admincerts
        copytree(org_user_msp_dir + '/signcerts/', org_user_msp_dir + '/admincerts')


# create ca-cert.pem file
def enrollCABootstrapAdmin(org):
    waitPort('%(CA_NAME)s to start' % {'CA_NAME': org['ca']['name']},
             90,
             org['ca']['logfile'],
             org['ca']['host'],
             org['ca']['port'])
    print('Enrolling with %(CA_NAME)s as bootstrap identity ...' % {'CA_NAME': org['ca']['name']}, flush=True)

    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': org['users']['bootstrap_admin']['name'],
        'pass': org['users']['bootstrap_admin']['pass'],
        'host': org['ca']['host'],
        'port': org['ca']['port']
    }

    call(['fabric-ca-client',
          'enroll', '-d',
          '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
          '-u', enrollment_url])

    # python sdk
    # caClient = ca_service(target=org['ca']['url'],
    #                       ca_certs_path=org['ca']['certfile'],
    #                       ca_name=org['ca']['name'])
    # enrollment = caClient.enroll(org['bootstrap_admin']['name'], org['bootstrap_admin']['pass'])


def registerOrdererIdentities(conf):
    for orderer in conf['orderers']:
        enrollCABootstrapAdmin(orderer)

        print('Registering %(orderer_name)s with %(ca_name)s' % {'orderer_name': orderer['name'],
                                                                 'ca_name': orderer['ca']['name']},
              flush=True)

        call(['fabric-ca-client',
              'register', '-d',
              '-c', '/root/cas/' + orderer['ca']['name'] + '/fabric-ca-client-config.yaml',
              '--id.name', orderer['users']['orderer']['name'],
              '--id.secret', orderer['users']['orderer']['name'],
              '--id.type', 'orderer'])

        print('Registering admin identity with %(ca_name)s' % {'ca_name': orderer['ca']['name']}, flush=True)

        # The admin identity has the "admin" attribute which is added to ECert by default
        call(['fabric-ca-client',
              'register', '-d',
              '-c', '/root/cas/' + orderer['ca']['name'] + '/fabric-ca-client-config.yaml',
              '--id.name', orderer['users']['admin']['name'],
              '--id.secret', orderer['users']['admin']['pass'],
              '--id.attrs', 'admin=true:ecert'])


def registerPeerIdentities(conf):
    for org in conf['orgs']:
        enrollCABootstrapAdmin(org)
        for peer in org['peers']:
            print('Registering %(peer_name)s with %(ca_name)s\n' % {'peer_name': peer['name'],
                                                                    'ca_name': org['ca']['name']}, flush=True)
            call(['fabric-ca-client', 'register', '-d',
                  '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
                  '--id.name', peer['name'],
                  '--id.secret', peer['pass'],
                  '--id.type', 'peer'])

        print('Registering admin identity with %(ca_name)s' % {'ca_name': org['ca']['name']}, flush=True)

        # The admin identity has the "admin" attribute which is added to ECert by default
        call(['fabric-ca-client',
              'register', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '--id.name', org['users']['admin']['name'],
              '--id.secret', org['users']['admin']['pass'],
              '--id.attrs',
              'hf.Registrar.Roles=client,hf.Registrar.Attributes=*,hf.Revoker=true,hf.GenCRL=true,admin=true:ecert,abac.init=true:ecert'
              ])

        print('Registering user identity with %(ca_name)s\n' % {'ca_name': org['ca']['name']}, flush=True)
        call(['fabric-ca-client',
              'register', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '--id.name', org['users']['user']['name'],
              '--id.secret', org['users']['user']['pass']])


def registerIdentities(conf):
    print('Registering identities...\n', flush=True)

    registerOrdererIdentities(conf)
    registerPeerIdentities(conf)


def registerUsers(conf):
    print('Getting CA certificates ...\n', flush=True)

    orgs = conf.get('orgs', [])
    for org in orgs:
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

    orderers = conf.get('orderers', [])
    for org in orderers:
        org_admin_msp_dir = org['users']['admin']['home'] + '/msp'

        # https://hyperledger-fabric.readthedocs.io/en/release-1.2/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # will create admincerts for configtxgen to work

        # register admin and create admincerts
        configLocalMSP(org, 'admin')
        # create tlscacerts directory and remove intermediatecerts if exists
        completeMSPSetup(org_admin_msp_dir)


def generateChannelArtifacts(conf):

    print('Generating channel configuration transaction at %(channel_tx_file)s' % {
        'channel_tx_file': conf['misc']['channel_tx_file']}, flush=True)

    call(['configtxgen',
          '-profile', 'OrgsChannel',
          '-outputCreateChannelTx', conf['misc']['channel_tx_file'],
          '-channelID', conf['misc']['channel_name']])

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


def generateGenesis(conf):
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

import sys

# from hfc.fabric_ca.caservice import ca_service
from subprocess import call, check_output, STDOUT, CalledProcessError

from util import waitPort, completeMSPSetup, configAdminLocalMSP, configUserLocalMSP
import os

dir_path = os.path.dirname(os.path.realpath(__file__))


def enrollCABootstrapAdmin(org):
    waitPort('%(CA_NAME)s to start' % {'CA_NAME': org['ca']['name']},
             90,
             org['ca']['logfile'],
             org['ca']['host'],
             org['ca']['port'])
    print('Enrolling with %(CA_NAME)s as bootstrap identity ...' % {'CA_NAME': org['ca']['name']}, flush=True)

    data = {
        'CA_ADMIN_USER_PASS': '%(name)s:%(pass)s' % {
            'name': org['users']['bootstrap_admin']['name'],
            'pass': org['users']['bootstrap_admin']['pass'],
        },
        'CA_URL': '%(host)s:%(port)s' % {'host': org['ca']['host'], 'port': org['ca']['port']}
    }

    call(['fabric-ca-client',
          'enroll', '-d',
          '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
          '-u', 'https://%(CA_ADMIN_USER_PASS)s@%(CA_URL)s' % data])

    # python sdk
    # caClient = ca_service(target=org['ca']['url'],
    #                       ca_certs_path=org['tls']['certfile'],
    #                       ca_name=org['ca']['name'])
    # enrollment = caClient.enroll(org['bootstrap_admin']['name'], org['bootstrap_admin']['pass'])


def registerOrdererIdentities(conf):
    for orderer_name in list(conf['orderers'].keys()):
        orderer = conf['orderers'][orderer_name]
        enrollCABootstrapAdmin(orderer)

        print('Registering %(orderer_name)s with %(ca_name)s' % {'orderer_name': orderer_name,
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
    for org_name in list(conf['orgs'].keys()):
        org = conf['orgs'][org_name]
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


def getCACerts(conf):
    print('Getting CA certificates ...\n', flush=True)

    for org_name in list(conf['orgs'].keys()):
        org = conf['orgs'][org_name]
        org_msp_dir = org['org_msp_dir']

        msg = 'Getting CA certs for organization %(org_name)s and storing in %(org_msp_dir)s'
        print(msg % {'org_msp_dir': org_msp_dir, 'org_name': org_name}, flush=True)

        # get ca-cert which will be the same a the tls cert...
        # http://hyperledger-fabric-ca.readthedocs.io/en/latest/users-guide.html#enabling-tls
        call(['fabric-ca-client',
              'getcacert', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '-u', org['ca']['url'],
              '-M', org_msp_dir])

        # https://hyperledger-fabric.readthedocs.io/en/release-1.1/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # create tlscacerts directory and remove intermediatecerts
        completeMSPSetup(org_msp_dir)
        configAdminLocalMSP(org)
        configUserLocalMSP(org_name, org)

    for org_name in list(conf['orderers'].keys()):
        org = conf['orderers'][org_name]
        org_msp_dir = org['org_msp_dir']

        msg = 'Getting CA certs for organization %(org_name)s and storing in %(org_msp_dir)s'
        print(msg % {'org_msp_dir': org_msp_dir, 'org_name': org_name}, flush=True)

        call(['fabric-ca-client',
              'getcacert', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '-u', org['ca']['url'],
              '-M', org_msp_dir])

        # create tlscacerts directory and remove intermediatecerts
        # https://hyperledger-fabric.readthedocs.io/en/release-1.1/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        completeMSPSetup(org_msp_dir)
        # will create admincerts for configtxgen to work
        configAdminLocalMSP(org)


def generateChannelArtifacts(conf):
    print('Generating orderer genesis block at %(genesis_bloc_file)s' % {
        'genesis_bloc_file': conf['misc']['genesis_bloc_file']}, flush=True)
    # Note: For some unknown reason (at least for now) the block file can't be
    # named orderer.genesis.block or the orderer will fail to launch

    # configtxgen -profile OrgsOrdererGenesis -outputBlock /data/genesis.block
    call(['configtxgen',
          '-profile', 'OrgsOrdererGenesis',
          '-outputBlock', conf['misc']['genesis_bloc_file']])

    print('Generating channel configuration transaction at %(channel_tx_file)s' % {
        'channel_tx_file': conf['misc']['channel_tx_file']}, flush=True)

    call(['configtxgen',
          '-profile', 'OrgsChannel',
          '-outputCreateChannelTx', conf['misc']['channel_tx_file'],
          '-channelID', conf['misc']['channel_name']])

    for org_name in list(conf['orgs'].keys()):
        org = conf['orgs'][org_name]
        print('Generating anchor peer update transaction for %(org_name)s at %(anchor_tx_file)s' % {
            'org_name': org_name,
            'anchor_tx_file': org['anchor_tx_file']
        }, flush=True)

        call(['configtxgen',
              '-profile', 'OrgsChannel',
              '-outputAnchorPeersUpdate', org['anchor_tx_file'],
              '-channelID', conf['misc']['channel_name'],
              '-asOrg', org_name])


if __name__ == '__main__':

    import json
    import argparse

    parser = argparse.ArgumentParser(description="Editeur")
    parser.add_argument('-c', '--config', nargs='?', type=str, action='store', default='', help="JSON config file to be used")
    args = vars(parser.parse_args())

    if args['config']:
        conf_path = os.path.join(dir_path, args['config'])
    else:
        conf_path = os.path.join(dir_path, 'conf.json')

    conf = json.load(open(conf_path, 'r'))

    registerIdentities(conf)
    getCACerts(conf)
    generateChannelArtifacts(conf)
    print('Finished building channel artifacts', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

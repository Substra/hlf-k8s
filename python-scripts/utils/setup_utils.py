import os
from subprocess import call

from hfc.fabric_ca.caservice import ca_service

from .common_utils import waitPort, completeMSPSetup, dowait, enrollWithFiles, writeFile


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
               [org['ca']['certfile']['internal']])

        msg = 'Enrolling user \'%(user_name)s\' for organization %(org)s with %(ca_host)s and home directory %(org_user_home)s...'
        print(msg % {
            'user_name': user['name'],
            'org': org['name'],
            'ca_host': org['ca']['host'],
            'org_user_home': org_user_home
        }, flush=True)

        enrollment = enrollWithFiles(user, org, org_user_msp_dir)

        # admincerts is required for configtxgen binary
        # will copy cert.pem from <user>/msp/signcerts to <user>/msp/admincerts
        # admincerts
        filename = os.path.join(org_user_msp_dir, 'admincerts', 'cert.pem')
        writeFile(filename, enrollment._cert)

        return enrollment


# create ca-cert.pem file
def enrollCABootstrapAdmin(org):
    waitPort('%(CA_NAME)s to start' % {'CA_NAME': org['ca']['name']},
             90,
             org['ca']['logfile'],
             org['ca']['host'],
             org['ca']['port']['internal'])
    print('Enrolling with %(CA_NAME)s as bootstrap identity ...' % {'CA_NAME': org['ca']['name']}, flush=True)

    target = "https://%s:%s" % (org['ca']['host'], org['ca']['port']['internal'])
    cacli = ca_service(target=target,
                       ca_certs_path=org['ca']['certfile']['internal'],
                       ca_name=org['ca']['name'])
    bootstrap_admin = cacli.enroll(org['users']['bootstrap_admin']['name'], org['users']['bootstrap_admin']['pass'])
    return bootstrap_admin


def registerOrdererIdentities(org):
    badmin = enrollCABootstrapAdmin(org)

    for orderer in org['orderers']:
        print('Registering %(orderer_name)s with %(ca_name)s' % {'orderer_name': orderer['name'],
                                                                 'ca_name': org['ca']['name']},
              flush=True)

        badmin.register(orderer['name'], orderer['pass'], 'orderer', maxEnrollments=-1)

    print('Registering admin identity with %(ca_name)s' % {'ca_name': org['ca']['name']}, flush=True)
    badmin.register(org['users']['admin']['name'], org['users']['admin']['pass'], maxEnrollments=-1, attrs=[{'admin': 'true:ecert'}])



def registerPeerIdentities(org):
    badmin = enrollCABootstrapAdmin(org)
    for peer in org['peers']:
        print('Registering %(peer_name)s with %(ca_name)s\n' % {'peer_name': peer['name'],
                                                                'ca_name': org['ca']['name']}, flush=True)
        badmin.register(peer['name'], peer['pass'], 'peer', maxEnrollments=-1)

    print('Registering admin identity with %(ca_name)s' % {'ca_name': org['ca']['name']}, flush=True)
    # The admin identity has the "admin" attribute which is added to ECert by default
    attrs = [
        {'hf.Registrar.Roles': 'client'},
        {'hf.Registrar.Attributess': '*'},
        {'hf.Revoker': 'true'},
        {'hf.GenCRL': 'true'},
        {'admin': 'true:ecert'},
        {'abac.init': 'true:ecert'}
    ]
    badmin.register(org['users']['admin']['name'], org['users']['admin']['pass'], maxEnrollments=-1, attrs=attrs)

    print('Registering user identity with %(ca_name)s\n' % {'ca_name': org['ca']['name']}, flush=True)
    badmin.register(org['users']['user']['name'], org['users']['user']['pass'], maxEnrollments=-1)


def registerIdentities(conf):
    if 'peers' in conf:
        registerPeerIdentities(conf)
    if 'orderers' in conf:
        registerOrdererIdentities(conf)


def registerUsers(conf):
    print('Getting CA certificates ...\n', flush=True)

    if 'peers' in conf:
        org_admin_msp_dir = conf['users']['admin']['home'] + '/msp'

        # will create admin and user folder with an msp folder and populate it. Populate admincerts for configtxgen to work
        # https://hyperledger-fabric.readthedocs.io/en/release-1.2/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp

        # enroll admin and create admincerts
        enrollmentAdmin = configLocalMSP(conf, 'admin')
        # needed for tls communication for create channel from peer for example, copy tlscacerts from cacerts
        completeMSPSetup(org_admin_msp_dir)

        # enroll user and create admincerts
        configLocalMSP(conf, 'user')
    else:
        org_admin_msp_dir = conf['users']['admin']['home'] + '/msp'

        # https://hyperledger-fabric.readthedocs.io/en/release-1.2/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # will create admincerts for configtxgen to work

        # enroll admin and create admincerts
        enrollmentAdmin = configLocalMSP(conf, 'admin')
        # create tlscacerts directory and remove intermediatecerts if exists
        completeMSPSetup(org_admin_msp_dir)

    return enrollmentAdmin


def generateGenesis(conf):
    print('Generating orderer genesis block at %(genesis_bloc_file)s' % {
        'genesis_bloc_file': conf['misc']['genesis_bloc_file']['external']
    }, flush=True)

    # Note: For some unknown reason (at least for now) the block file can't be
    # named orderer.genesis.block or the orderer will fail to launch

    # configtxgen -profile OrgsOrdererGenesis -channelID substrasystemchannel -outputBlock /substra/data/genesis/genesis.block
    call(['configtxgen',
          '-profile', 'OrgsOrdererGenesis',
          '-channelID', conf['misc']['system_channel_name'],
          '-outputBlock', conf['misc']['genesis_bloc_file']['external']])

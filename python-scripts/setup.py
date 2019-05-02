import json
from subprocess import call

from utils.setup_utils import registerIdentities, registerUsers, generateGenesis
from utils.common_utils import genTLSCert, create_directory
from shutil import copyfile


def init_org(conf):

    service = conf
    admin = service['users']['admin']
    org_admin_msp_dir = admin['home'] + '/msp'

    for peer in service['peers']:

        # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
        # except core.yaml from binded volume
        # call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp orderer.yaml configtx.yaml', shell=True)

        ##################################################################################################################
        # Although a peer may use the same TLS key and certificate file for both inbound and outbound TLS,               #
        # we generate a different key and certificate for inbound and outbound TLS simply to show that it is permissible #
        ##################################################################################################################

        enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
            'name': peer['name'],
            'pass': peer['pass'],
            'host': service['ca']['host'],
            'port': service['ca']['port']['internal']
        }

        # create external folder
        tls_server_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['server']['dir']
        tls_client_dir = peer['tls']['dir']['external'] + '/' + peer['tls']['client']['dir']
        create_directory(tls_server_dir)
        create_directory(tls_client_dir)

        # Generate server TLS cert and key pair in container
        genTLSCert(peer['host'],
                   '%s/%s' % (tls_server_dir, peer['tls']['server']['cert']),
                   '%s/%s' % (tls_server_dir, peer['tls']['server']['key']),
                   '%s/%s' % (tls_server_dir, peer['tls']['server']['ca']),
                   enrollment_url)

        # Generate client TLS cert and key pair for the peer CLI (will be used by external tools)
        # in a binded volume
        genTLSCert(peer['name'],
                   '%s/%s' % (tls_client_dir, peer['tls']['client']['cert']),
                   '%s/%s' % (tls_client_dir, peer['tls']['client']['key']),
                   '%s/%s' % (tls_client_dir, peer['tls']['client']['ca']),
                   enrollment_url)

        # Enroll the peer to get an enrollment certificate and set up the core's local MSP directory for starting peer
        setup_peer_msp_dir = service['core_dir']['internal'] + '/' + peer['name'] + '/msp'
        call(['fabric-ca-client',
              'enroll', '-d',
              '-u', enrollment_url,
              '-M', setup_peer_msp_dir])

        # copy the admincerts from the admin user for being able to install chaincode
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # https://lists.hyperledger.org/g/fabric/topic/17549225#1250
        # https://github.com/hyperledger/fabric-sdk-go/blob/master/internal/github.com/hyperledger/fabric/msp/mspimpl.go#L460
        # https://jira.hyperledger.org/browse/FAB-3840
        dst_admincerts_dir = setup_peer_msp_dir + '/admincerts'
        create_directory(dst_admincerts_dir)
        copyfile(org_admin_msp_dir + '/signcerts/cert.pem', '%s/%s-cert.pem' % (dst_admincerts_dir, admin['name']))


def init_orderer(conf):

    service = conf

    # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
    # except orderer.yaml from binded volume
    # call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp core.yaml configtx.yaml', shell=True)

    for orderer in service['orderers']:
        # Enroll to get orderer's TLS cert (using the "tls" profile)
        enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
            'name': orderer['name'],
            'pass': orderer['pass'],
            'host': service['ca']['host'],
            'port': service['ca']['port']['internal']
        }

        # create external folder
        tls_server_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['server']['dir']
        tls_client_dir = orderer['tls']['dir']['external'] + '/' + orderer['tls']['client']['dir']
        create_directory(tls_server_dir)
        create_directory(tls_client_dir)

        # Generate server TLS cert and key pair
        genTLSCert(orderer['host'],
                   '%s/%s' % (tls_server_dir, orderer['tls']['server']['cert']),
                   '%s/%s' % (tls_server_dir, orderer['tls']['server']['key']),
                   '%s/%s' % (tls_server_dir, orderer['tls']['server']['ca']),
                   enrollment_url)

        # Generate client TLS cert and key pair for the orderer CLI (will be used by external tools)
        # in a binded volume
        genTLSCert(orderer['host'],
                   '%s/%s' % (tls_client_dir, orderer['tls']['client']['cert']),
                   '%s/%s' % (tls_client_dir, orderer['tls']['client']['key']),
                   '%s/%s' % (tls_client_dir, orderer['tls']['client']['ca']),
                   enrollment_url)

        # Enroll again to get the orderer's enrollment certificate for getting signcert and being able to launch orderer
        setup_orderer_msp_dir = service['core_dir']['internal'] + '/' + orderer['name'] + '/msp'
        call(['fabric-ca-client',
              'enroll', '-d',
              '-u', enrollment_url,
              '-M', setup_orderer_msp_dir])

        # copy the admincerts from the admin user for being able to launch orderer
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # https://lists.hyperledger.org/g/fabric/topic/17549225#1250
        dst_admincerts_dir = setup_orderer_msp_dir + '/admincerts'
        create_directory(dst_admincerts_dir)
        copyfile('%s/signcerts/cert.pem' % setup_orderer_msp_dir, '%s/%s-cert.pem' % (dst_admincerts_dir, orderer['name']))


def init(conf):
    if 'peers' in conf:
        init_org(conf)
    if 'orderers' in conf:
        init_orderer(conf)
        create_directory(conf['broadcast_dir'])
        generateGenesis(conf)


if __name__ == '__main__':

    conf = json.load(open('/substra/conf.json', 'r'))
    registerIdentities(conf)
    registerUsers(conf)
    init(conf)
    print('Finished setup', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

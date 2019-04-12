import json
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call

from setup import registerPeerIdentities, registerUsers
from util import genTLSCert, create_directory
from shutil import copyfile


def init(conf):

    admin = conf['users']['admin']
    org_admin_msp_dir = admin['home'] + '/msp'

    for peer in conf['peers']:

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
            'host': conf['ca']['host'],
            'port': conf['ca']['port']
        }

        create_directory(peer['tls']['dir'])

        # Generate server TLS cert and key pair in container
        tlsdir = conf['core']['docker']['peer_home'] + '/tls'
        create_directory(tlsdir)
        genTLSCert(peer['host'],
                   peer['tls']['serverCert'],
                   peer['tls']['serverKey'],
                   peer['tls']['serverCa'],
                   enrollment_url)

        # Generate client TLS cert and key pair for the peer CLI (will be used by external tools)
        # in a binded volume
        genTLSCert(peer['name'],
                   peer['tls']['clientCert'],
                   peer['tls']['clientKey'],
                   peer['tls']['clientCa'],
                   enrollment_url)

        # Enroll the peer to get an enrollment certificate and set up the core's local MSP directory for starting peer
        call(['fabric-ca-client',
              'enroll', '-d',
              '-u', enrollment_url,
              '-M', conf['core']['docker']['msp_config_path'] + '/' + peer['name']])

        # copy the admincerts from the admin user for being able to install chaincode
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # https://lists.hyperledger.org/g/fabric/topic/17549225#1250
        # https://github.com/hyperledger/fabric-sdk-go/blob/master/internal/github.com/hyperledger/fabric/msp/mspimpl.go#L460
        # https://jira.hyperledger.org/browse/FAB-3840
        dst_ca_dir = conf['core']['docker']['msp_config_path'] + '/' + peer['name'] + '/admincerts/'
        create_directory(dst_ca_dir)
        copyfile(org_admin_msp_dir + '/signcerts/cert.pem', dst_ca_dir + '%s-cert.pem' % admin['name'])


if __name__ == '__main__':

    conf_path = '/substra/conf/conf-org.json'
    conf = json.load(open(conf_path, 'r'))

    conf['orderers'] = []  # Hack for setup
    registerPeerIdentities(conf)
    registerUsers(conf)
    init(conf['orgs'][0])

    print('Finished setup', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

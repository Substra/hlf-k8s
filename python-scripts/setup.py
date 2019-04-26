import json
from subprocess import call

from utils.setup_utils import registerIdentities, registerUsers, generateGenesis
from utils.common_utils import genTLSCert, create_directory
from shutil import copyfile


def init_org(conf):

    service = conf['service']
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
            'port': service['ca']['port']
        }

        create_directory(peer['tls']['dir'])

        # Generate server TLS cert and key pair in container
        tlsdir = service['core']['docker']['peer_home'] + '/tls'
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
              '-M', service['core']['docker']['msp_config_path'] + '/' + peer['name']])

        # copy the admincerts from the admin user for being able to install chaincode
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # https://lists.hyperledger.org/g/fabric/topic/17549225#1250
        # https://github.com/hyperledger/fabric-sdk-go/blob/master/internal/github.com/hyperledger/fabric/msp/mspimpl.go#L460
        # https://jira.hyperledger.org/browse/FAB-3840
        dst_ca_dir = service['core']['docker']['msp_config_path'] + '/' + peer['name'] + '/admincerts/'
        create_directory(dst_ca_dir)
        copyfile(org_admin_msp_dir + '/signcerts/cert.pem', dst_ca_dir + '%s-cert.pem' % admin['name'])


def init_orderer(conf):

    service = conf['service']
    admin = service['users']['admin']

    # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
    # except orderer.yaml from binded volume
    # call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp core.yaml configtx.yaml', shell=True)

    # Enroll to get orderer's TLS cert (using the "tls" profile)
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': admin['name'],
        'pass': admin['pass'],
        'host': service['ca']['host'],
        'port': service['ca']['port']
    }

    # Generate server TLS cert and key pair
    tlsdir = service['core']['host'] + '/tls'
    create_directory(tlsdir)
    tlsdockerdir = service['core']['docker'] + '/tls'
    create_directory(tlsdockerdir)
    genTLSCert(service['host'],
               service['tls']['cert'],
               service['tls']['key'],
               tlsdir + '/' + service['tls']['ca'],
               enrollment_url)

    # Generate client TLS cert and key pair for the orderer CLI (will be used by external tools)
    # in a binded volume
    create_directory(service['tls']['dir'])
    genTLSCert(service['host'],
               service['tls']['clientCert'],
               service['tls']['clientKey'],
               service['tls']['clientCa'],
               enrollment_url)

    # Enroll again to get the orderer's enrollment certificate for getting signcert and being able to launch orderer
    call(['fabric-ca-client',
          'enroll', '-d',
          '-u', enrollment_url,
          '-M', service['local_msp_dir']])

    # copy the admincerts from the admin user for being able to launch orderer
    # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
    # https://lists.hyperledger.org/g/fabric/topic/17549225#1250

    dst_ca_dir = '%s/admincerts/' % service['local_msp_dir']
    create_directory(dst_ca_dir)
    copyfile('%s/signcerts/cert.pem' % service['local_msp_dir'], '%s/%s-cert.pem' % (dst_ca_dir, admin['name']))

    create_directory(service['broadcast_dir'])

    generateGenesis(conf)


def init(conf):
    if 'peers' in conf['service']:
        init_org(conf)
    else:
        init_orderer(conf)


if __name__ == '__main__':

    conf = json.load(open('/substra/conf.json', 'r'))
    registerIdentities(conf)
    registerUsers(conf)
    init(conf)
    print('Finished setup', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

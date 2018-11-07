import os
from subprocess import call
from util import copyAdminCert, dowait, genTLSCert, create_directory
from conf import conf

if __name__ == '__main__':
    dowait("the 'setup' container to finish registering identities, creating the genesis block and other artifacts", 90,
           conf['misc']['setup_logfile'], [conf['misc']['setup_success_file']])

    org_name = os.environ['ORG']
    org = conf['orgs'][org_name]
    org_msp_dir = org['msp_dir']
    org_admin_msp_dir = org['users']['admin']['home'] + '/msp'
    peer = org['peers'][int(os.environ['PEER_INDEX'])]

    # Although a peer may use the same TLS key and certificate file for both inbound and outbound TLS,
    # we generate a different key and certificate for inbound and outbound TLS simply to show that it is permissible

    # Generate server TLS cert and key pair for the peer
    # fabric-ca-client enroll -d --enrollment.profile tls -u $ENROLLMENT_URL -M /tmp/tls --csr.hosts $PEER_HOST
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': peer['name'],
        'pass': peer['pass'],
        'host': org['ca']['host'],
        'port': org['ca']['port']
    }
    # generate cert and key in MSP folder /tmp/tls
    # Copy the TLS key and cert to the appropriate place with correct name
    tlsdir = org['core']['docker']['peer_home'] + '/tls'  # /opt/gopath/src/github.com/hyperledger/fabric/peer/tls
    create_directory(tlsdir)
    genTLSCert(peer['host'],
               tlsdir + '/' + org['core']['tls']['cert'],
               tlsdir + '/' + org['core']['tls']['key'],
               enrollment_url)

    create_directory(peer['tls']['dir'])
    # Generate client TLS cert and key pair for the peer CLI
    genTLSCert(peer['name'],
               peer['tls']['clientCert'],
               peer['tls']['clientKey'],
               enrollment_url)

    # Enroll the peer to get an enrollment certificate and set up the core's local MSP directory
    call(['fabric-ca-client',
          'enroll', '-d',
          '-u', enrollment_url,
          '-M', org['core']['docker']['msp_config_path']]) # '/opt/gopath/src/github.com/hyperledger/fabric/peer/msp'
    copyAdminCert(org_msp_dir + '/admincerts/cert.pem',  # '/substra/data/orgs/owkin/msp/admincerts/cert.pem '
                  org['core']['docker']['msp_config_path'] + '/admincerts', # '/opt/gopath/src/github.com/hyperledger/fabric/peer/msp'
                  org_name,
                  conf['misc']['setup_logfile'])

    # Start the peer
    print('Starting peer \'%(CORE_PEER_ID)s\' with MSP at \'%(CORE_PEER_MSPCONFIGPATH)s\'' % {
        'CORE_PEER_ID': peer['host'],
        'CORE_PEER_MSPCONFIGPATH': org['core']['docker']['msp_config_path']
    }, flush=True)
    call('env | grep CORE', shell=True)
    call(['peer', 'node', 'start'])

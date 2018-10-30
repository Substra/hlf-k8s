import os
from shutil import copy2
from subprocess import call
from util import completeMSPSetup, copyAdminCert, dowait, copy_last_file_ext, genClientTLSCert, create_directory
from conf import conf


if __name__ == '__main__':

    dowait("the 'setup' container to finish registering identities, creating the genesis block and other artifacts", 90, conf['misc']['setup_logfile'], [conf['misc']['setup_success_file']])

    org_name = os.environ['ORG']
    org = conf['orgs'][org_name]
    org_msp_dir = org['org_msp_dir']
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
    call(['fabric-ca-client',
          'enroll', '-d',
          '--enrollment.profile', 'tls',
          '-u', enrollment_url,
          '-M', '/tmp/tls',
          '--csr.hosts', peer['host']])

    # Copy the TLS key and cert to the appropriate place
    tlsdir = org['core']['docker']['peer_home'] + '/tls'
    create_directory(tlsdir)

    tlscert = tlsdir + '/' + org['core']['tls']['cert']
    tlskey = tlsdir + '/' + org['core']['tls']['key']
    copy2('/tmp/tls/signcerts/cert.pem', tlscert)
    copy_last_file_ext('*_sk', '/tmp/tls/keystore/', tlskey)
    call(['rm', '-rf', '/tmp/tls'])

    create_directory('/substra/data/orgs/' + org_name + '/tls/' + peer['name'])

    # Generate client TLS cert and key pair for the peer
    genClientTLSCert(peer['name'],
                     '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/client.crt',
                     '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/client.key',
                     enrollment_url)

    # Generate client TLS cert and key pair for the peer CLI
    genClientTLSCert(peer['name'],
                     '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.crt',
                     '/substra/data/orgs/' + org_name + '/tls/' + peer['name'] + '/cli-client.key',
                     enrollment_url)

    # Enroll the peer to get an enrollment certificate and set up the core's local MSP directory
    call(['fabric-ca-client',
          'enroll', '-d',
          '-u', enrollment_url,
          '-M', org['core']['docker']['msp_config_path']])

    completeMSPSetup(org['core']['docker']['msp_config_path'])

    copyAdminCert(org['core']['docker']['msp_config_path'], org_name, conf['misc']['setup_logfile'], org_msp_dir + '/admincerts/cert.pem')

    # Start the peer
    print('Starting peer \'%(CORE_PEER_ID)s\' with MSP at \'%(CORE_PEER_MSPCONFIGPATH)s\'' % {
        'CORE_PEER_ID': peer['host'],
        'CORE_PEER_MSPCONFIGPATH': org['core']['docker']['msp_config_path']
    }, flush=True)
    call('env | grep CORE', shell=True)
    call(['peer', 'node', 'start'])

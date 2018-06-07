import os
from shutil import copy2
from subprocess import call
from util import completeMSPSetup, copyAdminCert, dowait, copy_last_file_ext
from conf import conf
from util import create_directory

if __name__ == '__main__':

    dowait("the 'setup' container to finish registering identities, creating the genesis block and other artifacts", 90, conf['misc']['setup_logfile'], [conf['misc']['setup_success_file']])

    org_name = os.environ['ORG']
    org = conf['orderers'][org_name]

    # Enroll to get orderer's TLS cert (using the "tls" profile)
    # fabric-ca-client enroll -d --enrollment.profile tls -u $ENROLLMENT_URL -M /tmp/tls --csr.hosts $ORDERER_HOST
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': org['users']['admin']['name'],
        'pass': org['users']['admin']['pass'],
        'host': org['ca']['host'],
        'port': org['ca']['port']
    }
    call(['fabric-ca-client',
          'enroll', '-d',
          '--enrollment.profile', 'tls',
          '-u', enrollment_url,
          '-M', '/tmp/tls',
          '--csr.hosts', org['host']])

    # Copy the TLS key and cert to the appropriate place
    tlsdir = org['home'] + '/tls'
    create_directory(tlsdir)

    tlscert = tlsdir + '/' + org['tls']['cert']
    tlskey = tlsdir + '/' + org['tls']['key']
    copy2('/tmp/tls/signcerts/cert.pem', tlscert)
    copy_last_file_ext('*_sk', '/tmp/tls/keystore/', tlskey)
    call(['rm', '-rf', '/tmp/tls'])

    # Enroll again to get the orderer's enrollment certificate (default profile)
    # fabric-ca-client enroll -d -u $ENROLLMENT_URL -M $ORDERER_GENERAL_LOCALMSPDIR
    call(['fabric-ca-client', 'enroll', '-d', '-u', enrollment_url, '-M', org['local_msp_dir']])

    # Finish setting up the local MSP for the orderer
    completeMSPSetup(org['local_msp_dir'])

    org_msp_dir = org['org_msp_dir']
    copyAdminCert(org['local_msp_dir'], org_name, conf['misc']['setup_logfile'], org_msp_dir + '/admincerts/cert.pem')

    # Wait for the genesis block to be created
    dowait("genesis block to be created", 60, conf['misc']['setup_logfile'], [conf['misc']['genesis_bloc_file']])

    create_directory(org['broadcast_dir'])

    # Start the orderer
    call('env | grep ORDERER', shell=True)
    call(['orderer'])
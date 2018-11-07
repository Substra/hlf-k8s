import json
import os
from subprocess import call
from util import copyAdminCert, dowait, genTLSCert, create_directory
conf_path = '/substra/conf/conf.json'

conf = json.load(open(conf_path, 'r'))

if __name__ == '__main__':

    dowait("the 'setup' container to finish registering identities, creating the genesis block and other artifacts", 90, conf['misc']['setup_logfile'], [conf['misc']['setup_success_file']])

    org_name = os.environ['ORG']
    org = conf['orderers'][org_name]
    org_admin_msp_dir = org['users']['admin']['home'] + '/msp'

    # Enroll to get orderer's TLS cert (using the "tls" profile)
    # fabric-ca-client enroll -d --enrollment.profile tls -u $ENROLLMENT_URL -M /tmp/tls --csr.hosts $ORDERER_HOST
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': org['users']['admin']['name'],
        'pass': org['users']['admin']['pass'],
        'host': org['ca']['host'],
        'port': org['ca']['port']
    }
    # Copy the TLS key and cert to the appropriate place
    tlsdir = org['home'] + '/tls'
    create_directory(tlsdir)
    tlscert = tlsdir + '/' + org['tls']['cert']
    tlskey = tlsdir + '/' + org['tls']['key']
    genTLSCert(org['host'], tlscert, tlskey, enrollment_url)

    # Enroll again to get the orderer's enrollment certificate (default profile)
    # fabric-ca-client enroll -d -u $ENROLLMENT_URL -M $ORDERER_GENERAL_LOCALMSPDIR
    call(['fabric-ca-client', 'enroll', '-d', '-u', enrollment_url, '-M', org['local_msp_dir']])
    copyAdminCert(org_admin_msp_dir + '/admincerts/cert.pem', org['local_msp_dir'] + '/admincerts', org_name, conf['misc']['setup_logfile'])

    # Wait for the genesis block to be created
    dowait("genesis block to be created", 60, conf['misc']['setup_logfile'], [conf['misc']['genesis_bloc_file']])

    create_directory(org['broadcast_dir'])

    # Start the orderer
    call('env | grep ORDERER', shell=True)
    call(['orderer'])

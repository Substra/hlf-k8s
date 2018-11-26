import json
import os
from shutil import copyfile
from subprocess import call
from util import dowait, genTLSCert, create_directory

conf_path = '/substra/conf/conf.json'

conf = json.load(open(conf_path, 'r'))

if __name__ == '__main__':

    org_name = os.environ['ORG']
    org = conf['orderers'][org_name]
    admin = org['users']['admin']
    org_admin_msp_dir = admin['home'] + '/msp'

    # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
    # except orderer.yaml from binded volume
    call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp core.yaml configtx.yaml', shell=True)


    # Enroll to get orderer's TLS cert (using the "tls" profile)
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': admin['name'],
        'pass': admin['pass'],
        'host': org['ca']['host'],
        'port': org['ca']['port']
    }

    # Generate server TLS cert and key pair
    tlsdir = org['home'] + '/tls'
    create_directory(tlsdir)
    genTLSCert(org['host'],
               tlsdir + '/' + org['tls']['cert'],
               tlsdir + '/' + org['tls']['key'],
               enrollment_url)

    # Enroll again to get the orderer's enrollment certificate for getting signcert and being able to launch orderer
    call(['fabric-ca-client',
          'enroll', '-d',
          '-u', enrollment_url,
          '-M', org['local_msp_dir']])

    # copy the admincerts from the admin user for being able to launch orderer
    # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
    # https://lists.hyperledger.org/g/fabric/topic/17549225#1250

    dst_ca_dir = './fabric/msp/admincerts/'
    create_directory(dst_ca_dir)
    copyfile('%s/signcerts/cert.pem' % org['local_msp_dir'], '%s/admincerts/%s-cert.pem' % (org['local_msp_dir'], admin['name']))

    # Wait for the genesis block to be created
    dowait("genesis block to be created", 60, conf['misc']['setup_logfile'], [conf['misc']['genesis_bloc_file']])

    create_directory(org['broadcast_dir'])

    # Start the orderer
    call('env | grep ORDERER', shell=True)
    call(['orderer'])

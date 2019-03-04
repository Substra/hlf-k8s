import json
import os
from shutil import copyfile
from subprocess import call
from util import dowait, genTLSCert, create_directory

conf_path = '/substra/conf/conf.json'

conf = json.load(open(conf_path, 'r'))

if __name__ == '__main__':

    admin = conf['users']['admin']
    org_admin_msp_dir = admin['home'] + '/msp'

    # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
    # except orderer.yaml from binded volume
    call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp core.yaml configtx.yaml', shell=True)


    # Enroll to get orderer's TLS cert (using the "tls" profile)
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': admin['name'],
        'pass': admin['pass'],
        'host': conf['ca']['host'],
        'port': conf['ca']['port']
    }

    # Generate server TLS cert and key pair
    tlsdir = conf['home'] + '/tls'
    create_directory(tlsdir)
    genTLSCert(conf['host'],
               tlsdir + '/' + conf['tls']['cert'],
               tlsdir + '/' + conf['tls']['key'],
               tlsdir + '/' + conf['tls']['ca'],
               enrollment_url)

    # Enroll again to get the orderer's enrollment certificate for getting signcert and being able to launch orderer
    call(['fabric-ca-client',
          'enroll', '-d',
          '-u', enrollment_url,
          '-M', conf['local_msp_dir']])

    # copy the admincerts from the admin user for being able to launch orderer
    # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
    # https://lists.hyperledger.org/g/fabric/topic/17549225#1250

    dst_ca_dir = '%s/admincerts/' % conf['local_msp_dir']
    create_directory(dst_ca_dir)
    copyfile('%s/signcerts/cert.pem' % conf['local_msp_dir'], '%s/%s-cert.pem' % (dst_ca_dir, admin['name']))

    # Wait for the genesis block to be created
    dowait("genesis block to be created", 60, conf['misc']['setup_logfile'], [conf['misc']['genesis_bloc_file']])

    create_directory(conf['broadcast_dir'])

    # Start the orderer
    call('env | grep ORDERER', shell=True)
    call(['orderer'])

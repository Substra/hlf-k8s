import json
from subprocess import call
from shutil import copyfile
from utils.setup_utils import registerOrdererIdentities, registerUsers, generateGenesis
from utils.common_utils import genTLSCert, create_directory


def init(orderer_conf):

    admin = orderer_conf['users']['admin']

    # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
    # except orderer.yaml from binded volume
    # call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp core.yaml configtx.yaml', shell=True)

    # Enroll to get orderer's TLS cert (using the "tls" profile)
    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': admin['name'],
        'pass': admin['pass'],
        'host': orderer_conf['ca']['host'],
        'port': orderer_conf['ca']['port']
    }

    # Generate server TLS cert and key pair
    tlsdir = orderer_conf['core']['host'] + '/tls'
    create_directory(tlsdir)
    tlsdockerdir = orderer_conf['core']['docker'] + '/tls'
    create_directory(tlsdockerdir)
    genTLSCert(orderer_conf['host'],
               orderer_conf['tls']['cert'],
               orderer_conf['tls']['key'],
               tlsdir + '/' + orderer_conf['tls']['ca'],
               enrollment_url)

    # Generate client TLS cert and key pair for the orderer CLI (will be used by external tools)
    # in a binded volume
    create_directory(orderer_conf['tls']['dir'])
    genTLSCert(orderer_conf['host'],
               orderer_conf['tls']['clientCert'],
               orderer_conf['tls']['clientKey'],
               orderer_conf['tls']['clientCa'],
               enrollment_url)

    # Enroll again to get the orderer's enrollment certificate for getting signcert and being able to launch orderer
    call(['fabric-ca-client',
          'enroll', '-d',
          '-u', enrollment_url,
          '-M', orderer_conf['local_msp_dir']])

    # copy the admincerts from the admin user for being able to launch orderer
    # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
    # https://lists.hyperledger.org/g/fabric/topic/17549225#1250

    dst_ca_dir = '%s/admincerts/' % orderer_conf['local_msp_dir']
    create_directory(dst_ca_dir)
    copyfile('%s/signcerts/cert.pem' % orderer_conf['local_msp_dir'], '%s/%s-cert.pem' % (dst_ca_dir, admin['name']))

    create_directory(orderer_conf['broadcast_dir'])


if __name__ == '__main__':

    conf = json.load(open('/substra/conf/conf.json', 'r'))

    registerOrdererIdentities(conf)
    registerUsers(conf)
    init(conf['orderers'][0])
    generateGenesis(conf)
    print('Finished setup orderer.', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

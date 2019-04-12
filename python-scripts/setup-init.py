import json
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call
from shutil import copyfile
from setup import registerOrdererIdentities, registerUsers, generateGenesis
from util import genTLSCert, create_directory


def init(conf):
    admin = conf['users']['admin']

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
    tlsdir = conf['core']['host'] + '/tls'
    create_directory(tlsdir)
    tlsdockerdir = conf['core']['docker'] + '/tls'
    create_directory(tlsdockerdir)
    genTLSCert(conf['host'],
               conf['tls']['cert'],
               conf['tls']['key'],
               tlsdir + '/' + conf['tls']['ca'],
               enrollment_url)

    create_directory(conf['tls']['dir'])
    # Generate client TLS cert and key pair for the orderer CLI (will be used by external tools)
    # in a binded volume
    genTLSCert(conf['host'],
               conf['tls']['clientCert'],
               conf['tls']['clientKey'],
               conf['tls']['clientCa'],
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

    create_directory(conf['broadcast_dir'])


if __name__ == '__main__':

    conf_path = '/substra/conf/conf.json'
    conf = json.load(open(conf_path, 'r'))

    registerOrdererIdentities(conf)
    conf['orgs'] = []  # Hack for setup
    registerUsers(conf)
    for orderer in conf['orderers']:
        init(orderer)
    generateGenesis(conf)
    print('Finished building channel artifacts', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

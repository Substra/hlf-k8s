import json
import os
from subprocess import call

from utils.setup_utils import registerIdentities, registerUsers, generateGenesis, enrollWithFiles, genTLSCert, writeFile
from utils.common_utils import create_directory


def generateMSPandTLS(node, org, msp_dir, admincerts=False):
    ##################################################################################################################
    # Although a peer may use the same TLS key and certificate file for both inbound and outbound TLS,               #
    # we generate a different key and certificate for inbound and outbound TLS simply to show that it is permissible #
    ##################################################################################################################

    # Node peer/orderer mounted volume, see docker_utils 'Client/Server TLS' binded volume.
    tls_setup_dir = node['tls']['dir']['external']

    # create external folders (client and server)
    tls_server_dir = os.path.join(tls_setup_dir, node['tls']['server']['dir'])
    tls_client_dir = os.path.join(tls_setup_dir, node['tls']['client']['dir'])

    # Generate server TLS cert and key pair in container
    genTLSCert(node, org,
               cert_file=os.path.join(tls_server_dir, node['tls']['server']['cert']),
               key_file=os.path.join(tls_server_dir, node['tls']['server']['key']),
               ca_file=os.path.join(tls_server_dir, node['tls']['server']['ca']))

    # Generate client TLS cert and key pair for the peer CLI (will be used by external tools)
    # in a binded volume
    genTLSCert(node, org,
               cert_file=os.path.join(tls_client_dir, node['tls']['client']['cert']),
               key_file=os.path.join(tls_client_dir, node['tls']['client']['key']),
               ca_file=os.path.join(tls_client_dir, node['tls']['client']['ca']))

    # Enroll the node to get an enrollment certificate and set up the core's local MSP directory for starting node
    enrollWithFiles(node, org, msp_dir, admincerts=admincerts)


def init_org(conf, enrollmentAdmin):

    for peer in conf['peers']:
        setup_peer_msp_dir = os.path.join(conf['core_dir']['internal'], peer['name'], 'msp')
        generateMSPandTLS(peer, conf, setup_peer_msp_dir, admincerts=False)

        # copy the admincerts from the admin user for being able to install chaincode
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # https://lists.hyperledger.org/g/fabric/topic/17549225#1250
        # https://github.com/hyperledger/fabric-sdk-go/blob/master/internal/github.com/hyperledger/fabric/msp/mspimpl.go#L460
        # https://jira.hyperledger.org/browse/FAB-3840
        admin = conf['users']['admin']
        filename = os.path.join(setup_peer_msp_dir, 'admincerts', '%s-cert.pem' % admin['name'])
        writeFile(filename, enrollmentAdmin._cert)


def init_orderer(conf):
    for orderer in conf['orderers']:
        setup_orderer_msp_dir = os.path.join(conf['core_dir']['internal'], orderer['name'], 'msp')
        # copy the admincerts from the user for being able to launch orderer
        generateMSPandTLS(orderer, conf, setup_orderer_msp_dir, admincerts=True)


def init(conf, enrollmentAdmin):
    if 'peers' in conf:
        init_org(conf, enrollmentAdmin)
    if 'orderers' in conf:
        init_orderer(conf)
        create_directory(conf['broadcast_dir']['external'])
        generateGenesis(conf)


if __name__ == '__main__':

    conf = json.load(open('/substra/conf.json', 'r'))
    registerIdentities(conf)
    enrollmentAdmin = registerUsers(conf)
    init(conf, enrollmentAdmin)
    print('Finished setup', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

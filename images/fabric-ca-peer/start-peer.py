# There are really two "types" of MSPs:
#
# An MSP which is used as a signing identity
# For the default MSP type (X509-based), the signing identity uses the crypto material in the keystore (private key) and
# signcerts (X509 public key which matches the keystore private key). Peers and orderers use their "local MSP" for
# signing; examples would be peers signing endorsement responses and orderers signing blocks (deliver responses)
#
# An MSP which is used to verify signatures / identities
# In this case, when a node needs to verify the signature (e.g. a peer verifying the signature of an endorsement
# proposal from a client), it will extract the MSPID from the creator field in the message it receives, look to see if
#  t has a copy of the MSP for that MSPID.
#
# If the role requires MEMBER, it then uses the "cacerts" / "intermediatecerts" content to verify that the identity was
# indeed issued by that MSP. It then uses the public key which is also in the creator field to validate the signature.
#
# In the case where an ADMIN role is required, it actually checks to make sure that the creator public key is an exact
# match for one of the X509 public certs in the "admincerts" folder.
#
# NOTE: There is technically no difference between an "admin" cert and a "member" cert. An identity becomes an "ADMIN"
#  role by simply adding the public certificate to the "admincerts" folder of the MSP.
#
# NOTE: The MSPs for all members of a channel are distributed to all the peers that are part of a channel via config
# blocks. The orderer also has the MSPs for all members of each channel / consortium as well.

import json
import os
from shutil import copyfile
from subprocess import call
from util import genTLSCert, create_directory

conf_path = '/substra/conf/conf.json'

conf = json.load(open(conf_path, 'r'))

if __name__ == '__main__':
    org_name = os.environ['ORG']
    org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    admin = org['users']['admin']
    org_admin_msp_dir = admin['home'] + '/msp'
    peer = org['peers'][int(os.environ['PEER_INDEX'])]

    # remove ugly sample files defined here https://github.com/hyperledger/fabric/tree/master/sampleconfig
    # except core.yaml from binded volume
    call('cd $FABRIC_CA_CLIENT_HOME && rm -rf msp orderer.yaml configtx.yaml', shell=True)

    ##################################################################################################################
    # Although a peer may use the same TLS key and certificate file for both inbound and outbound TLS,               #
    # we generate a different key and certificate for inbound and outbound TLS simply to show that it is permissible #
    ##################################################################################################################

    enrollment_url = 'https://%(name)s:%(pass)s@%(host)s:%(port)s' % {
        'name': peer['name'],
        'pass': peer['pass'],
        'host': org['ca']['host'],
        'port': org['ca']['port']
    }

    create_directory(peer['tls']['dir'])

    # Generate server TLS cert and key pair in container
    tlsdir = org['core']['docker']['peer_home'] + '/tls'
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
          '-M', org['core']['docker']['msp_config_path']])

    # copy the admincerts from the admin user for being able to install chaincode
    # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
    # https://lists.hyperledger.org/g/fabric/topic/17549225#1250
    # https://github.com/hyperledger/fabric-sdk-go/blob/master/internal/github.com/hyperledger/fabric/msp/mspimpl.go#L460
    # https://jira.hyperledger.org/browse/FAB-3840
    dst_ca_dir = org['core']['docker']['msp_config_path'] + '/admincerts/'
    create_directory(dst_ca_dir)
    copyfile(org_admin_msp_dir + '/signcerts/cert.pem', dst_ca_dir + '%s-cert.pem' % admin['name'])

    # Start the peer
    print('Starting peer \'%(CORE_PEER_ID)s\' with MSP at \'%(CORE_PEER_MSPCONFIGPATH)s\'' % {
        'CORE_PEER_ID': peer['host'],
        'CORE_PEER_MSPCONFIGPATH': org['core']['docker']['msp_config_path']
    }, flush=True)
    call('env | grep CORE', shell=True)
    call(['peer', 'node', 'start'])

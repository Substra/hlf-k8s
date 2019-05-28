import os
import glob
import socket

import time
from shutil import copytree, copy2
from subprocess import call, check_output

from hfc.fabric_ca.caservice import ca_service
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes


def writeFile(filename, content):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'wb') as f:
        f.write(content)


def saveMSP(msp_dir, enrollment, admincerts=False):
    # cert
    filename = os.path.join(msp_dir, 'signcerts', 'cert.pem')
    writeFile(filename, enrollment._cert)

    # private key
    if enrollment._private_key:
        private_key = enrollment._private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                            format=serialization.PrivateFormat.PKCS8,
                                                            encryption_algorithm=serialization.NoEncryption())
        filename = os.path.join(msp_dir, 'keystore', 'key.pem')
        writeFile(filename, private_key)

    # ca
    filename = os.path.join(msp_dir, 'cacerts', 'ca.pem')
    writeFile(filename, enrollment._caCert)

    if admincerts:
        filename = os.path.join(msp_dir, 'admincerts', 'cert.pem')
        writeFile(filename, enrollment._cert)


def enrollWithFiles(user, org, msp_dir, csr=None, profile='', attr_reqs=None, admincerts=False):
    target = "https://%s:%s" % (org['ca']['host'], org['ca']['port']['internal'])
    cacli = ca_service(target=target,
                       ca_certs_path=org['ca']['certfile'],
                       ca_name=org['ca']['name'])
    enrollment = cacli.enroll(user['name'], user['pass'], csr=csr, profile=profile, attr_reqs=attr_reqs)

    saveMSP(msp_dir, enrollment, admincerts=admincerts)

    return enrollment


def removeIntermediateCerts(intermediatecerts_dir):
    print('Delete intermediate certs in ' + intermediatecerts_dir, flush=True)
    if os.path.exists(intermediatecerts_dir):
        for file in os.listdir(intermediatecerts_dir):
            file_path = os.path.join(intermediatecerts_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)


def completeMSPSetup(org_msp_dir):
    src = org_msp_dir + '/cacerts/'
    dst = org_msp_dir + '/tlscacerts'

    if not os.path.exists(dst):
        copytree(src, dst)

    # intermediate cacert management
    if os.path.exists(org_msp_dir + '/intermediatecerts'):
        # no intermediate cert in this config, delete generated files for not seeing warning
        removeIntermediateCerts(org_msp_dir + '/intermediatecerts/')

        # uncomment if using intermediate certs
        # copytree(org_msp_dir + '/intermediatecerts/', org_msp_dir + '/tlsintermediatecerts/')


def genTLSCert(node, host_name, org, cert_file, key_file, ca_file):
    # Generate our key
    pkey = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend())

    # Generate a CSR
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        # Provide various details about who we are.
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"FR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Loire Atlantique"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"NAntes"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"owkin"),
        x509.NameAttribute(NameOID.COMMON_NAME, node['name']),
    ])).add_extension(
        x509.SubjectAlternativeName([
            # Describe what sites we want this certificate for.
            x509.DNSName(host_name),
        ]),
        critical=False,
        # Sign the CSR with our private key.
    ).sign(pkey, hashes.SHA256(), default_backend())

    target = "https://%s:%s" % (org['ca']['host'], org['ca']['port']['internal'])
    cacli = ca_service(target=target,
                       ca_certs_path=org['ca']['certfile'],
                       ca_name=org['ca']['name'])
    enrollment = cacli.enroll(node['name'], node['pass'], csr=csr, profile='tls')

    # cert
    writeFile(cert_file, enrollment._cert)

    # private key
    private_key = pkey.private_bytes(encoding=serialization.Encoding.PEM,
                                     format=serialization.PrivateFormat.PKCS8,
                                     encryption_algorithm=serialization.NoEncryption())
    writeFile(key_file, private_key)

    # ca
    writeFile(ca_file, enrollment._caCert)


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


# Wait for a process to begin to listen on a particular host and port
# Usage: waitPort <what> <timeoutInSecs> <errorLogFile> <host> <port>
def waitPort(what, secs, logFile, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))

    if result != 0:
        print('Waiting for %s ...' % what, flush=True)
        starttime = int(time.time())

        while True:
            call(['sleep', '1'])
            result = sock.connect_ex((host, port))
            if result == 0:
                break

            if int(time.time()) - starttime > secs:
                print('Failed waiting for %(what)s; see %(logFile)s' % {'what': what, 'logFile': logFile}, flush=True)
                break

            print('.', end='', flush=True)


# Wait for one or more files to exist
def dowait(what, secs, logFile, files):
    logit = True
    starttime = int(time.time())

    for file in files:
        while not os.path.exists(file):
            if logit:
                print('Waiting for %s ...\n' % what, flush=True)
                logit = False
            call(['sleep', '1'])
            if int(time.time()) - starttime > secs:
                print('Failed waiting for %(what)s; see %(logFile)s\n' % {'what': what, 'logFile': logFile}, flush=True)
                break
            print('.', end='', flush=True)
    print('')

# Remove chaincode docker images
def remove_chaincode_docker_images():
    chaincodeImages = check_output('docker images | grep "^dev-peer" | awk \'{print $3}\'', shell=True)

    if chaincodeImages:
        print('Removing chaincode docker images ...', flush=True)
        call('docker rmi -f ' + chaincodeImages.decode('utf-8').replace('\n', ' '), shell=True)


# Remove chaincode docker containers
def remove_chaincode_docker_containers():
    chaincodeContainers = check_output('docker ps -a | grep "dev-peer" | awk \'{print $1}\'', shell=True)

    if chaincodeContainers:
        print('Removing chaincode docker containers ...', flush=True)
        call('docker rm -f ' + chaincodeContainers.decode('utf-8').replace('\n', ' '), shell=True)

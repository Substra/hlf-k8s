import os
import glob
import socket

import time
from shutil import copytree, copy2
from subprocess import call, check_output


def copy_last_file_ext(ext, src, dst):
    files = glob.iglob(os.path.join(src, ext))
    for file in files:
        if os.path.isfile(file):
            copy2(file, dst)


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


def genTLSCert(host_name, cert_file, key_file, ca_file, enrollment_url):
    call(['fabric-ca-client',
          'enroll', '-d',
          '--enrollment.profile', 'tls',
          '-u', enrollment_url,
          '-M', '/tmp/tls',
          '--csr.hosts', host_name])

    copy2('/tmp/tls/signcerts/cert.pem', cert_file)
    copy_last_file_ext('*_sk', '/tmp/tls/keystore/', key_file)
    copy_last_file_ext('*.pem', '/tmp/tls/tlscacerts/', ca_file)
    call(['rm', '-rf', '/tmp/tls'])


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

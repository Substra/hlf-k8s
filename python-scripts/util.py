import os
import glob
import socket

import time
from shutil import copytree, copy2
from subprocess import call, check_output, CalledProcessError, STDOUT


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
    for file in os.listdir(intermediatecerts_dir):
        file_path = os.path.join(intermediatecerts_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)


def completeMSPSetup(org_msp_dir):
    src = org_msp_dir + '/cacerts/'
    dst = org_msp_dir + '/tlscacerts'
    if not os.path.exists(dst):
        copytree(src, dst)

        if os.path.exists(org_msp_dir + '/intermediatecerts'):
            # no intermediate cert in this config, delete generated files for not seeing warning
            removeIntermediateCerts(org_msp_dir + '/intermediatecerts/')

            # uncomment if using intermediate certs
            # copytree(org_msp_dir + '/intermediatecerts/', org_msp_dir + '/tlsintermediatecerts/')


def genClientTLSCert(host_name, cert_file, key_file, enrollment_url):
    call(['fabric-ca-client',
          'enroll', '-d',
          '--enrollment.profile', 'tls',
          '-u', enrollment_url,
          '-M', '/tmp/tls',
          '--csr.hosts', host_name])

    create_directory('/data/tls')
    copy2('/tmp/tls/signcerts/cert.pem', cert_file)
    copy_last_file_ext('*_sk', '/tmp/tls/keystore/', key_file)
    call(['rm', '-rf', '/tmp/tls'])


# Copy the org's admin cert into some target MSP directory
# This is only required if ADMINCERTS is enabled.
def copyAdminCert(msp_config_path, org, setup_log_file, org_admin_cert):
    dstDir = msp_config_path + '/admincerts'
    create_directory(dstDir)
    dowait('%s administator to enroll' % org, 60, setup_log_file, [org_admin_cert])
    copy2(org_admin_cert, dstDir)


def configAdminLocalMSP(org):
    org_admin_home = org['admin_home']
    org_msp_dir = org['org_msp_dir']
    org_admin_msp_dir = org_admin_home + '/msp'

    # if local admin msp does not exist, create it by enrolling admin
    if not os.path.exists(org_admin_msp_dir):
        print('enroll admin and copy in admincert', flush=True)

        # wait tls certfile exists before enrolling
        dowait('%(ca_name)s to start' % {'ca_name': org['ca']['name']},
               90,
               org['ca']['logfile'],
               [org['tls']['certfile']])

        print('Enrolling admin \'%(admin_name)s\' with %(ca_host)s...' % {'admin_name': org['users']['admin']['name'],
                                                                          'ca_host': org['ca']['host']},
              flush=True)

        data = {
            'CA_ADMIN_USER_PASS': '%(name)s:%(pass)s' % {
                'name': org['users']['admin']['name'],
                'pass': org['users']['admin']['pass'],
            },
            'CA_URL': '%(host)s:%(port)s' % {'host': org['ca']['host'], 'port': org['ca']['port']}
        }

        call(['fabric-ca-client',
              'enroll', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '-u', 'https://%(CA_ADMIN_USER_PASS)s@%(CA_URL)s' % data,
              '-M', org_admin_msp_dir])  # :warning: note the msp dir

        # no intermediate cert in this config, delete generated files for not seeing warning
        removeIntermediateCerts(org_admin_msp_dir + '/intermediatecerts/')

        # If admincerts are required in the MSP, copy the cert there now and to my local MSP also
        # admincerts is required for configtxgen binary
        create_directory(org_msp_dir + '/admincerts/')
        copy2(org_admin_msp_dir + '/signcerts/cert.pem', org_msp_dir + '/admincerts/cert.pem')

        # copy signcerts to admincerts
        copytree(org_admin_msp_dir + '/signcerts/', org_admin_msp_dir + '/admincerts')


# Switch to the current org's user identity.  Enroll if not previously enrolled.
def configUserLocalMSP(org_name, org):
    org_admin_home = org['admin_home']
    org_user_home = org['user_home']
    org_user_msp_dir = org_user_home + '/msp'

    if not os.path.exists(org_user_msp_dir):
        dowait('%(CA_NAME)s to start' % {'CA_NAME': org['ca']['name']},
               60,
               org['ca']['logfile'],
               [org['tls']['certfile']])

        print('Enrolling user for organization %(org)s with home directory %(org_user_home)s...' % {
            'org': org_name,
            'org_user_home': org_user_home}, flush=True)

        data = {
            'USER_CREDENTIALS': '%(name)s:%(pass)s' % {
                'name': org['users']['user']['name'],
                'pass': org['users']['user']['pass'],
            },
            'CA_URL': '%(host)s:%(port)s' % {'host': org['ca']['host'], 'port': org['ca']['port']}
        }

        call(['fabric-ca-client',
              'enroll', '-d',
              '-c', '/root/cas/' + org['ca']['name'] + '/fabric-ca-client-config.yaml',
              '-u', 'https://%(USER_CREDENTIALS)s@%(CA_URL)s' % data,
              '-M', org_user_msp_dir])

        # no intermediate cert in this config, delete generated files for not seeing warning
        removeIntermediateCerts(org_user_msp_dir + '/intermediatecerts/')

        # Set up admincerts directory if required
        copytree(org_admin_home + '/msp/signcerts/', org_user_home + '/msp/admincerts')

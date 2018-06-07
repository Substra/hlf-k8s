#!/bin/bash
#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

# set -e
#
# # Initialize the root CA
# cd /etc/hyperledger/fabric-ca-server
#
# # check cert generated files
# # openssl x509 -in ca-cert.pem -text -noout
#
# # remove generated examples crt files by default for using those from config file with init generation
# rm -rf *.pem # ca-cert.pem, ca-key.pem
#
# # will create ca-cert.pem, fabric-ca-server.db, msp
# fabric-ca-server init -d -c fabric-ca-server-config.yaml
# #fabric-ca-server init -d -c fabric-ca-server-config.yaml -b $USER_PASS
#
# # check cert generated files
# openssl x509 -in ca-cert.pem -text -noout
#
# # Copy the root CA's signing certificate to the data directory to be used by others (especially setup)
# cp -r $FABRIC_CA_HOME/ca-cert.pem $TARGET_CERTFILE
#
# # Start the root CA
# fabric-ca-server start
import os
from os import chdir
from subprocess import call

if __name__ == '__main__':

    print('Initialize the root CA', flush=True)

    chdir('/etc/hyperledger/fabric-ca-server')

    print('remove generated examples crt files by default for using those from config file with init generation', flush=True)

    # http: // fabric - ca.readthedocs.io / en / latest / users - guide.html  # initializing-the-server
    # If custom values for the CSR are required, you may customize the configuration file, delete the files specified by the ca.certfile and ca-keyfile configuration items, and then run the fabric-ca-server init -b admin:adminpw command again.
    # by default the docker image copy these files from payload examples and init does not overwrite them
    call('rm -rf *.pem', shell=True)  # ca-cert.pem, ca-key.pem

    # will create ca-cert.pem, fabric-ca-server.db, msp
    call('fabric-ca-server init -d -c fabric-ca-server-config.yaml', shell=True)

    print('Copy the root CA\'s signing certificate to the data directory to be used by others (especially setup)', flush=True)

    call('cp -r %(FABRIC_CA_HOME)s/ca-cert.pem %(TARGET_CERTFILE)s' % {
        'FABRIC_CA_HOME': os.environ['FABRIC_CA_HOME'],
        'TARGET_CERTFILE': os.environ['TARGET_CERTFILE']
    }, shell=True)

    print('Start the root CA', flush=True)
    call('fabric-ca-server start', shell=True)
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

from subprocess import call

if __name__ == '__main__':

    print('Start the root CA', flush=True)
    call('fabric-ca-server start', shell=True)

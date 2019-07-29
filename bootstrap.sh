#!/bin/bash
#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

BASEDIR=$(dirname "$0")

createCustomDockerImages() {
    for dir in $BASEDIR/images/*/; do
        dir=`basename $dir`
        docker build -t substra/$dir -f $BASEDIR/images/$dir/Dockerfile .
    done
}

echo "===> List out hyperledger docker images"
docker images | grep hyperledger/fabric-ca*

echo "===> Create custom docker images"
createCustomDockerImages

#!/bin/bash
#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

BASEDIR=$(dirname "$0")

# if version not passed in, default to latest released version
export VERSION=1.2.1
# if ca version not passed in, default to latest released version
export CA_VERSION=$VERSION
# current version of thirdparty images (couchdb, kafka and zookeeper) released
export THIRDPARTY_IMAGE_VERSION=0.4.10
export ARCH=$(echo "$(uname -s|tr '[:upper:]' '[:lower:]'|sed 's/mingw64_nt.*/windows/')-$(uname -m | sed 's/x86_64/amd64/g')")
export MARCH=$(uname -m)

dockerCaPull() {
      local CA_TAG=$1
      echo "==> FABRIC CA IMAGE"
      echo
      for image in "" "-tools" "-orderer" "-peer"; do
         docker pull hyperledger/fabric-ca${image}:$CA_TAG
         docker tag hyperledger/fabric-ca${image}:$CA_TAG hyperledger/fabric-ca${image}
      done
}

createCustomDockerImages() {
    for dir in $BASEDIR/images/*/; do
        dir=`basename $dir`
        docker build -t substra/$dir $BASEDIR/images/$dir
    done
}

# starting with 1.2.0, multi-arch images will be default
: ${CA_TAG:="$CA_VERSION"}

BINARY_FILE=hyperledger-fabric-${ARCH}-${VERSION}.tar.gz
CA_BINARY_FILE=hyperledger-fabric-ca-${ARCH}-${CA_VERSION}.tar.gz

echo "===> Pulling fabric ca Image"
dockerCaPull ${CA_TAG}

echo "===> List out hyperledger docker images"
docker images | grep hyperledger/fabric-ca*

echo "===> Create custom docker images"
createCustomDockerImages
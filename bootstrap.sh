#!/bin/bash
#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

BASEDIR=$(dirname "$0")

# if version not passed in, default to latest released version
export VERSION=1.2.0
# if ca version not passed in, default to latest released version
export CA_VERSION=$VERSION
# current version of thirdparty images (couchdb, kafka and zookeeper) released
export THIRDPARTY_IMAGE_VERSION=0.4.10
export ARCH=$(echo "$(uname -s|tr '[:upper:]' '[:lower:]'|sed 's/mingw64_nt.*/windows/')-$(uname -m | sed 's/x86_64/amd64/g')")
export MARCH=$(uname -m)

dockerFabricPull() {
  local FABRIC_TAG=$1
  for IMAGES in peer orderer ccenv tools; do
      echo "==> FABRIC IMAGE: $IMAGES"
      echo
      docker pull hyperledger/fabric-$IMAGES:$FABRIC_TAG
      docker tag hyperledger/fabric-$IMAGES:$FABRIC_TAG hyperledger/fabric-$IMAGES
  done
}

dockerCaPull() {
      local CA_TAG=$1
      echo "==> FABRIC CA IMAGE"
      echo
      docker pull hyperledger/fabric-ca:$CA_TAG
      docker tag hyperledger/fabric-ca:$CA_TAG hyperledger/fabric-ca
}

createCustomDockerImages() {
    for dir in $BASEDIR/images/*/; do
        dir=`basename $dir`
        docker build -t substra/$dir $BASEDIR/images/$dir
    done
}

binariesInstall() {
  echo "===> Downloading version ${FABRIC_TAG} platform specific fabric binaries"
  binaryDownload ${BINARY_FILE} https://nexus.hyperledger.org/content/repositories/releases/org/hyperledger/fabric/hyperledger-fabric/${ARCH}-${VERSION}/${BINARY_FILE}
  if [ $? -eq 22 ]; then
     echo
     echo "------> ${FABRIC_TAG} platform specific fabric binary is not available to download <----"
     echo
   fi

  echo "===> Downloading version ${CA_TAG} platform specific fabric-ca-client binary"
  binaryDownload ${CA_BINARY_FILE} https://nexus.hyperledger.org/content/repositories/releases/org/hyperledger/fabric-ca/hyperledger-fabric-ca/${ARCH}-${CA_VERSION}/${CA_BINARY_FILE}
  if [ $? -eq 22 ]; then
     echo
     echo "------> ${CA_TAG} fabric-ca-client binary is not available to download  (Available from 1.1.0-rc1) <----"
     echo
   fi
}

# starting with 1.2.0, multi-arch images will be default
: ${CA_TAG:="$CA_VERSION"}
: ${FABRIC_TAG:="$VERSION"}

BINARY_FILE=hyperledger-fabric-${ARCH}-${VERSION}.tar.gz
CA_BINARY_FILE=hyperledger-fabric-ca-${ARCH}-${CA_VERSION}.tar.gz

echo "===> Pulling fabric Images"
dockerFabricPull ${FABRIC_TAG}
echo "===> Pulling fabric ca Image"
dockerCaPull ${CA_TAG}

echo "===> List out hyperledger docker images"
docker images | grep hyperledger*

echo "===> Create custom docker images"
createCustomDockerImages
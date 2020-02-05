#!/bin/bash
#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

BASEDIR=$(dirname "$0")

# if version not passed in, default to latest released version
export VERSION=1.4.3
# if ca version not passed in, default to latest released version
export CA_VERSION=$VERSION
# current version of thirdparty images (couchdb, kafka and zookeeper) released
export THIRDPARTY_IMAGE_VERSION=0.4.15
export ARCH=$(echo "$(uname -s|tr '[:upper:]' '[:lower:]'|sed 's/mingw64_nt.*/windows/')-$(uname -m | sed 's/x86_64/amd64/g')")
export MARCH=$(uname -m)

# starting with 1.2.0, multi-arch images will be default
: ${CA_TAG:="$CA_VERSION"}
: ${FABRIC_TAG:="$VERSION"}

BINARY_FILE=hyperledger-fabric-${ARCH}-${VERSION}.tar.gz
CA_BINARY_FILE=hyperledger-fabric-ca-${ARCH}-${CA_VERSION}.tar.gz

# This will download the .tar.gz
download() {
    local BINARY_FILE=$1
    local URL=$2
    echo "===> Downloading: " "${URL}"
    wget "${URL}" || rc=$?
    tar xvzf "${BINARY_FILE}" || rc=$?
    rm "${BINARY_FILE}"
    if [ -n "$rc" ]; then
        echo "==> There was an error downloading the binary file."
        return 22
    else
        echo "==> Done."
    fi
}

binariesInstall() {
  echo "===> Downloading version ${CA_TAG} platform specific fabric-ca-client binary"
  download "${CA_BINARY_FILE}" "https://github.com/hyperledger/fabric-ca/releases/download/v${CA_VERSION}/${CA_BINARY_FILE}"
  if [ $? -eq 22 ]; then
    echo
    echo "------> ${CA_TAG} fabric-ca-client binary is not available to download  (Available from 1.1.0-rc1) <----"
    echo
    exit
  fi
}

binariesInstall

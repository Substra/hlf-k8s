#!/bin/bash
# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- CHAINCODE_NAME Chaincode name (required)"
    echo -e "\t- CHAINCODE_VERSION Chaincode version (required)"
    echo -e "\t- CHAINCODE_SRC Chaincode release archive url (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 mycc 1.0 https://github.com/SubstraFoundation/substra-chaincode/archive/master.tar.gz"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function installChaincode() {
    if [ ! $# == 3 ]; then
        help
        exit 1
    fi

    CHAINCODE_NAME=$1
    CHAINCODE_VERSION=$2
    CHAINCODE_SRC=$3

    peer chaincode list --installed | grep $CHAINCODE_NAME | grep $CHAINCODE_VERSION
    if [ $? -eq 0 ]; then
        echo "Chaincode already exists. Skipping."
    else
      if [[ -z "${GITHUB_TOKEN}" ]]; then
        curl -L $CHAINCODE_SRC -o chaincode.tar.gz
      else
        curl --header "Authorization: token $GITHUB_TOKEN" -L $CHAINCODE_SRC -o chaincode.tar.gz
      fi

      mkdir substra-chaincode
      tar -C substra-chaincode -xvzf chaincode.tar.gz --strip-components=1
      mkdir -p /opt/gopath/src/github.com/hyperledger
      mv substra-chaincode/chaincode /opt/gopath/src/chaincode
      peer chaincode install -n $CHAINCODE_NAME -v $CHAINCODE_VERSION -p chaincode
    fi
}

installChaincode $@

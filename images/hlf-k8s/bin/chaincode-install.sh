#!/bin/bash

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
      curl --header "Authorization: token $GITHUB_TOKEN" -L $CHAINCODE_SRC -o chaincode.tar.gz
      tar xvzf chaincode.tar.gz
      mkdir -p /opt/gopath/src/github.com/hyperledger
      mv substra-chaincode-$(basename $CHAINCODE_SRC .tar.gz)/chaincode /opt/gopath/src/chaincode
      peer chaincode install -n $CHAINCODE_NAME -v $CHAINCODE_VERSION -p chaincode
    fi
}

installChaincode $@

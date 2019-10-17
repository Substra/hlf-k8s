#!/bin/bash

help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- CHANNEL_ID Channel to create (required)"
    echo -e "\t- ORDERER_URL Orderer url (required)"
    echo -e "\t- CHAINCODE_NAME Chaincode name (required)"
    echo -e "\t- CHAINCODE_VERSION Chaincode version (required)"
    echo -e "\t- CHAINCODE_POLICY for the chaincode policy in the channel (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 mychannel https://myorderer.myorg.com:443 mycc 1.0 \"OR('MyOrg1MSP.member','MyOrg2MSP.member')\""
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function instantiateChaincode() {
    if [ ! $# == 5 ]; then
        help
        exit 1
    fi

    CHANNEL_ID=$1
    ORDERER_URL=$2
    CHAINCODE_NAME=$3
    CHAINCODE_VERSION=$4
    CHAINCODE_POLICY=$5

    peer chaincode -C $CHANNEL_ID list --instantiated | grep $CHAINCODE_NAME | grep $CHAINCODE_VERSION
    if [ $? -eq 0 ]; then
        echo "Chaincode already instantiated. Skipping."
    else
      until peer chaincode instantiate -C $CHANNEL_ID -n $CHAINCODE_NAME -v $CHAINCODE_VERSION -c '{"Args":["init"]}' -P "$CHAINCODE_POLICY" -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt 1>/dev/null 2>/dev/null
      do
        echo "\033[0;31m Failed instanciating chaincode $CHAINCODE_NAME at version $CHAINCODE_VERSION on channel $CHANNEL_ID \033[0m"
        sleep 5
      done
    fi
}

instantiateChaincode $@

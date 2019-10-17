#!/bin/bash

help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- SYSTEM_CHANNEL_ID System channel to use to generate the genesis block (required)"
    echo -e "\t- SECRET_NAME Name of the secret to be generated (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 systemChannelId secretName"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

if [ ! $# == 2 ]; then
    help
    exit 1
fi

function generateGenesis() {
    SYSTEM_CHANNEL_ID=$1
    SECRET_NAME=$2

    kubectl get secret $SECRET_NAME 1> /dev/null 2> /dev/null
    if [ $? -eq 0 ]; then
        echo "Genesis file already present. Skipping."
    else
        configtxgen -profile OrgsOrdererGenesis -channelID $SYSTEM_CHANNEL_ID -outputBlock genesis.block --configPath /etc/hyperledger/fabric
        kubectl create secret generic $SECRET_NAME --from-file=genesis.block
    fi
}

generateGenesis $@

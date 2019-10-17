#!/bin/bash

help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- CHANNEL_ID Channel to create (required)"
    echo -e "\t- ORDERER_URL Orderer url (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 mychannel https://myorderer.myorg.com:443"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function joinChannel() {
    if [ ! $# == 2 ]; then
        help
        exit 1
    fi

    CHANNEL_ID=$1
    ORDERER_URL=$2

    peer channel list | grep $CHANNEL_ID
    if [ $? -eq 0 ]; then
        echo "Channel already joined. Skipping."
    else
        printf 'Fetching channel block from the orderer:'
        until $(peer channel fetch oldest channel.block -c $CHANNEL_ID -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt); do
            printf '.'
            sleep 2
        done

        peer channel join -b channel.block
    fi
}

joinChannel $@

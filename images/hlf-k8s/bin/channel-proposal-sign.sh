#!/bin/bash
help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- PROPOSAL_PATH Path of the proposal file to sign (required)"
    echo -e "\t- ORDERER_URL url of the orderer (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 ./proposal.pb organizationName"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function channelProposalSign() {
    if [[ ! $# -eq 2 ]]; then
        echo "Error: Illegal number of parameters"
        help
        exit 1
    fi

    PROPOSAL_PATH=$1
    ORDERER_URL=$2

    printf 'Testing the connection with the orderer:'
    until $(curl --output /dev/null --silent --head $ORDERER_URL); do
        printf '.'
        sleep 2
    done

    peer channel signconfigtx -f $PROPOSAL_PATH -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt
}

channelProposalSign $@

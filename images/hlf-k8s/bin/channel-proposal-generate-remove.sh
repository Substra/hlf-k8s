#!/bin/bash
help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- CHANNEL_ID System channel name (required)"
    echo -e "\t- ORDERER_URL url of the orderer (required)"
    echo -e "\t- ORGANIZATION_NAME Name of the organization to add to the channel (required)"
    echo -e "\t- IS_SYSTEM If you want to update a system channel, then turn this flag to true (optional, default false)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 systemChannelId ordererUrl organizationName true"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function channelProposalGenerate() {
    if [ ! $# -eq 3 ]; then
        if [ ! $# -eq 4 ]; then
            echo "Error: Illegal number of parameters"
            help
            exit 1
        fi
    fi

    local CHANNEL_ID=$1
    local ORDERER_URL=$2
    local ORGANIZATION_NAME=$3
    local IS_SYSTEM=${4:-false}

    printf 'Testing the connection with the orderer:'
    until $(curl --output /dev/null --silent --head $ORDERER_URL); do
        printf '.'
        sleep 2
    done

    peer channel fetch config channel.block -c $CHANNEL_ID -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt
    configtxlator proto_decode --input channel.block --type common.Block | jq .data.data[0].payload.data.config > channelconfig.json
    configtxlator proto_encode --input channelconfig.json --type common.Config --output channelold.block

    if [ "$IS_SYSTEM" = true ]; then
        jq "del(.channel_group.groups.Consortiums.groups.SampleConsortium.groups.$ORGANIZATION_NAME)" channelconfig.json -c > newchannel.json
    else
        jq "del(.channel_group.groups.Application.groups.$ORGANIZATION_NAME)" channelconfig.json -c > newchannel.json
    fi

    configtxlator proto_encode --input newchannel.json --type common.Config --output channelupdate.block
    configtxlator compute_update --channel_id $CHANNEL_ID --original channelold.block --updated channelupdate.block | configtxlator proto_decode --type common.ConfigUpdate --output compute_update.json
    echo '{"payload":{"header":{"channel_header":{"channel_id": "'$CHANNEL_ID'", "type":2}},"data":{"config_update":'$(cat compute_update.json)'}}}' > proposal.json
    configtxlator proto_encode --input proposal.json --type common.Envelope --output proposal.pb
}

channelProposalGenerate $@

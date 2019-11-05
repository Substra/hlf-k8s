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
    echo -e "\t- CHANNEL_ID System channel name (required)"
    echo -e "\t- ORDERER_URL url of the orderer (required)"
    echo -e "\t- ORGANIZATION_NAME Name of the organization to add to the channel (required)"
    echo -e "\t- CONFIG_PATH Path of the organization config json (required)"
    echo -e "\t- IS_SYSTEM If you want to update a system channel, then turn this flag to true (optional, default false)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 systemChannelId ordererUrl organizationName ./anchor-config.json true"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function channelProposalGenerate() {
    if [ ! $# -eq 4 ]; then
        if [ ! $# -eq 5 ]; then
            echo "Error: Illegal number of parameters"
            help
            exit 1
        fi
    fi

    local CHANNEL_ID=$1
    local ORDERER_URL=$2
    local ORGANIZATION_NAME=$3
    local CONFIG_PATH=$4
    local IS_SYSTEM=${5:-false}

    printf 'Testing the connection with the orderer:'
    until $(curl --output /dev/null --silent --head $ORDERER_URL); do
        printf '.'
        sleep 2
    done

    peer channel fetch config channel.block -c $CHANNEL_ID -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt
    configtxlator proto_decode --input channel.block --type common.Block | jq .data.data[0].payload.data.config > channelconfig.json
    configtxlator proto_encode --input channelconfig.json --type common.Config --output channelold.block

    if [ "$IS_SYSTEM" = true ]; then
        jq -s '.[0] * {"channel_group":{"groups":{"Consortiums":{"groups":{"SampleConsortium":{"groups":{"'$ORGANIZATION_NAME'":.[1]}}}}}}}' channelconfig.json $CONFIG_PATH > channelconfigUpdated.json
    else
        jq -s '.[0] * {"channel_group":{"groups":{"Application":{"groups":{"'$ORGANIZATION_NAME'":.[1]}}}}}' channelconfig.json $CONFIG_PATH > channelconfigUpdated.json
    fi

    configtxlator proto_encode --input channelconfigUpdated.json --type common.Config --output channelupdate.block
    configtxlator compute_update --channel_id $CHANNEL_ID --original channelold.block --updated channelupdate.block | configtxlator proto_decode --type common.ConfigUpdate | jq . > compute_update.json
    echo '{"payload":{"header":{"channel_header":{"channel_id": "'$CHANNEL_ID'", "type":2}},"data":{"config_update":'$(cat compute_update.json)'}}}' | jq . > proposal.json
    configtxlator proto_encode --input proposal.json --type common.Envelope --output proposal.pb
}

channelProposalGenerate $@

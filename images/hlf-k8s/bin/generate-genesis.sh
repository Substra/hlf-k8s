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

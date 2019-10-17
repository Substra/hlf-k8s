#!/bin/bash

help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- SECRET_NAME Name of the configmap that will be generated (required)"
    echo -e "\t- ORGANIZATION_NAME Organization name for the anchored peer (required)"
    echo -e "\t- PEER_HOST Organization Peer host address for the anchored peer (required)"
    echo -e "\t- PEER_PORT Organization Peer port value for the anchored peer (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 myorg mysecret"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function prepareOrgConfig() {
    if [ ! $# == 4 ]; then
        help
        exit 1
    fi

    SECRET_NAME=$1
    SECRET_NAME_ANCHOR=$1"-anchor"
    ORGANIZATION_NAME=$2
    PEER_HOST=$3
    PEER_PORT=$4

    kubectl get secret $SECRET_NAME 1> /dev/null 2> /dev/null
    if [ $? -eq 0 ]; then
        echo "Organization config secret already exists. Skipping."
    else
        configtxgen -printOrg $ORGANIZATION_NAME > configOrg.json
        kubectl create secret generic $SECRET_NAME --from-file=configOrg.json

        # Config with anchor
        jq -s '.[0] * {"values":{"AnchorPeers":{"mod_policy":"Admins", "value":{"anchor_peers":[{"host":"'$PEER_HOST'", "port":"'$PEER_PORT'"}]}, "version": "0"}}}' configOrg.json > configOrgWithAnchors.json
        kubectl create secret generic $SECRET_NAME_ANCHOR --from-file=configOrgWithAnchors.json
    fi
}

prepareOrgConfig $@

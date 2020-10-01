#!/bin/bash

# This script creates HLF kubernetes secrets for orderer, org-1 and org-2.
#
# To speed up local deployment, run this script before running `skaffold run`:
#
#   $ ./examples/dev-secrets.sh create
#   $ skaffold run

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
KUBECTL="kubectl"

if [ "$1" != "create" ] && [ "$1" != "delete" ]; then
    echo "Usage: dev-secrets.sh [create|delete]"
    exit
fi

OP=$1
if [ "$OP" == "create" ]; then
    OP="apply"
fi

if [ -n "$KUBE_CONTEXT" ]; then
    KUBECTL="kubectl --context=${KUBE_CONTEXT}"
fi

if [ "$OP" = "apply" ]; then
    ${KUBECTL} create namespace orderer
    ${KUBECTL} create namespace org-1
    ${KUBECTL} create namespace org-2
fi

${KUBECTL} "$OP" -f "${DIR}/secrets/secrets-orderer-genesis.yaml"
${KUBECTL} "$OP" -f "${DIR}/secrets/secrets-orderer.yaml"
${KUBECTL} "$OP" -f "${DIR}/secrets/secrets-org-1.yaml"
${KUBECTL} "$OP" -f "${DIR}/secrets/secrets-org-2.yaml"

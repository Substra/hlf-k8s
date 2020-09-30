#!/bin/bash

# This script creates HLF kubernetes secrets for orderer, org-1 and org-2.
#
# To speed up local deployment, run this script before running `skaffold run`:
#
#   $ ./examples/secrets-create.sh
#   $ skaffold run

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OP="apply"

if [ "$1" == "delete" ]; then
    OP="delete"
fi

if [ "$OP" = "apply" ]; then
    kubectl create namespace orderer
    kubectl create namespace org-1
    kubectl create namespace org-2
fi

kubectl "$OP" -f "${DIR}/secrets/secrets-orderer-genesis.yaml"
kubectl "$OP" -f "${DIR}/secrets/secrets-orderer.yaml"
kubectl "$OP" -f "${DIR}/secrets/secrets-org-1.yaml"
kubectl "$OP" -f "${DIR}/secrets/secrets-org-2.yaml"

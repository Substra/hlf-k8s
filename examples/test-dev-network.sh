#!/bin/bash

# (Local development script)
# This script verifies that the network is functional by invoking a smart
# contract on each node.
#
# Usage:
#   ./test-dev-network.sh N
#   where N is the number of nodes on your network
#
# Example:
#  ./test-dev-network.sh 2
#

NUM_ORGS=${1:-2}
PARAMS='{\"msg\":\"{\\\"filter\\\":{}}\",\"request_id\":\"30a59245\"}'

for i in `seq $NUM_ORGS`; do
    echo org-$i
    kubectl exec -it -n org-$i `kubectl get pods -n org-$i | grep toolbox | cut -d' ' -f1` -- \
    bash -c "peer chaincode invoke \
        -C mychannel \
        -n mycc \
        --tls \
        --clientauth \
        --cafile /var/hyperledger/tls/ord/cert/cacert.pem \
        --certfile /var/hyperledger/tls/server/pair/tls.crt \
        --keyfile /var/hyperledger/tls/server/pair/tls.key \
        -o network-orderer-hlf-ord.orderer.svc.cluster.local:7050 \
        -c '{\"Args\":[\"orchestrator.computetask:QueryTasks\", \"${PARAMS}\"]}'"
    echo '-----------'
done

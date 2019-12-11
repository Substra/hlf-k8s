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
    echo -e "\t- CA_POD_SELECTOR The label selector of the CA pod (required)"
    echo -e "\t- ADMIN_USERNAME admin username to register (required)"
    echo -e "\t- ADMIN_PASSWORD admin password to register (required)"
    echo -e "\t- ADMIN_ATTRS --id.attrs option (required)"
    echo -e "\t- USER_USERNAME user username to register (required)"
    echo -e "\t- USER_PASSWORD user password to register (required)"
    echo -e "\t- USER_TYPE --id.type option (required)"
    echo -e "\t- CSR_HOSTS Host of the orderer (required)"
    echo ""
    echo "Options:"
    echo -e "\t- -h, --help \t Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 substra-ca-release admin adminpwd admin=true:ecert sarah-mollit mypoorpwd orderer http://orderer.localhost"
}

if [[ $1 == "-h" ||$1 == "--help" ]]; then
    help
    exit 0
fi

function bootstrap() {
    if [[ ! $# -eq 8 ]]; then
        echo "Error: Illegal number of parameters"
        help
        exit 1
    fi

    CA_POD_SELECTOR=$1
    ADMIN_USERNAME=$2
    ADMIN_PASSWORD=$3
    ADMIN_ATTRS=$4
    USER_USERNAME=$5
    USER_PASSWORD=$6
    USER_TYPE=$7
    CSR_HOSTS=$8

    CA_POD_NAME=$(kubectl get pods -l "$CA_POD_SELECTOR" -o jsonpath="{.items[0].metadata.name}")

    printf 'Testing the connection with the CA:'
    until [[ "$(kubectl get po "$CA_POD_NAME" -o 'jsonpath={.status.conditions[?(@.type=="Ready")].status}')" == 'True' ]]; do
        printf '.'
        sleep 2
    done

    TMP_DIR=$(mktemp -d)
    MSP_ADMIN_DIR=$TMP_DIR/mspAdmin
    MSP_USER_DIR=$TMP_DIR/mspUser
    TLS_ADMIN_DIR=$TMP_DIR/tlsAdmin
    TLS_USER_DIR=$TMP_DIR/tlsUser

    # Generate certificates/keys
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client enroll -d -u http://\$CA_ADMIN:\$CA_PASSWORD@\$SERVICE_DNS:7054"
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client register -d -u http://\$CA_ADMIN:\$CA_PASSWORD@\$SERVICE_DNS:7054 --id.name $ADMIN_USERNAME --id.secret $ADMIN_PASSWORD --id.attrs \"$ADMIN_ATTRS\""
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client register -d -u http://\$CA_ADMIN:\$CA_PASSWORD@\$SERVICE_DNS:7054 --id.name $USER_USERNAME --id.secret $USER_PASSWORD --id.type $USER_TYPE"
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client enroll -d -u http://$ADMIN_USERNAME:$ADMIN_PASSWORD@\$SERVICE_DNS:7054 -M $MSP_ADMIN_DIR"
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client enroll -d -u http://$USER_USERNAME:$USER_PASSWORD@\$SERVICE_DNS:7054 -M $MSP_USER_DIR"
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client enroll -d --enrollment.profile tls -u http://$ADMIN_USERNAME:$ADMIN_PASSWORD@\$SERVICE_DNS:7054 -M $TLS_ADMIN_DIR --csr.hosts $CSR_HOSTS"
    kubectl exec $CA_POD_NAME -- bash -c "fabric-ca-client enroll -d --enrollment.profile tls -u http://$USER_USERNAME:$USER_PASSWORD@\$SERVICE_DNS:7054 -M $TLS_USER_DIR --csr.hosts $CSR_HOSTS"

    # Fetch certificates/keys from CA pod
    kubectl cp $CA_POD_NAME:/var/hyperledger/fabric-ca/msp/certs/ /tmp/certs
    kubectl cp $CA_POD_NAME:$MSP_ADMIN_DIR /tmp/mspAdmin
    kubectl cp $CA_POD_NAME:$MSP_USER_DIR /tmp/mspUser
    kubectl cp $CA_POD_NAME:$TLS_ADMIN_DIR /tmp/tlsAdmin
    kubectl cp $CA_POD_NAME:$TLS_USER_DIR /tmp/tlsUser

    # Normalize file names
    mv /tmp/certs/*-cert.pem /tmp/certs/cacert.pem
    mv /tmp/mspAdmin/keystore/* /tmp/mspAdmin/keystore/key.pem
    mv /tmp/mspUser/keystore/* /tmp/mspUser/keystore/key.pem
    mv /tmp/tlsAdmin/tlscacerts/* /tmp/tlsAdmin/tlscacerts/cacert.pem
    mv /tmp/tlsUser/tlscacerts/* /tmp/tlsUser/tlscacerts/cacert.pem

    # Create secrets
    kubectl create secret generic $SECRET_NAME_CERT --from-file=/tmp/mspUser/signcerts/cert.pem
    kubectl create secret generic $SECRET_NAME_KEY --from-file=/tmp/mspUser/keystore/key.pem
    kubectl create secret generic $SECRET_NAME_CACERT --from-file=/tmp/certs/cacert.pem
    kubectl create secret tls $SECRET_NAME_TLS_SERVER --key $(find /tmp/tlsAdmin/keystore -type f) --cert /tmp/tlsAdmin/signcerts/cert.pem
    kubectl create secret tls $SECRET_NAME_TLS_CLIENT --key $(find /tmp/tlsUser/keystore -type f) --cert /tmp/tlsUser/signcerts/cert.pem
    kubectl create secret generic $SECRET_NAME_TLS_SERVER_ROOT --from-file=/tmp/tlsAdmin/tlscacerts/cacert.pem
    kubectl create secret generic $SECRET_NAME_TLS_CLIENT_ROOT --from-file=/tmp/tlsUser/tlscacerts/cacert.pem
    kubectl create secret generic $SECRET_NAME_ADMIN_CERT --from-file=/tmp/mspAdmin/signcerts/cert.pem
    kubectl create secret generic $SECRET_NAME_ADMIN_KEY --from-file=/tmp/mspAdmin/keystore/key.pem

    if [ "$USER_TYPE" == "orderer" ]; then
        kubectl create secret generic $SECRET_NAME_TLS_ORD_ROOT --from-file=/tmp/tlsUser/tlscacerts/cacert.pem
    fi
}

bootstrap $@

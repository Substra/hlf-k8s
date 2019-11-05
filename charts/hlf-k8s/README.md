# Network package of Substra

## Requirements

Having a Kubernetes cluster working with Helm initialized. You can do thant locally by installing Minikube and grabbing Helm binary from github.
Then simply launch your cluster using `minikube start` and configure helm with `helm init`.

## Install the package
```
helm install --name network owkin/hlf-k8s
```

### Cleanup
```
helm delete --purge network
```

## Usage

### Add an organization to the system channel
You will need to copy the org-config secret generated from the new peer org to the orderer.
Then add the organization to the orderer values and upgrade (This will generate a job and use the previously copied secret)

### Create an application channel from MyPeer1
```
channel-create.sh mychannel orderer-hlf-ord:7050 MyPeer1
```

### Add organization MyPeer2 to the application channel from MyPeer1

```
kubectl get secret peer-2-org-config -o jsonpath='{.data.configOrgWithAnchors\.json}' | base64 -d > ./anchor.json
channel-proposal-generate-add.sh mychannel orderer-hlf-ord:7050 MyPeer1 ./anchor.json
channel-proposal-sign.sh ./proposal.pb orderer-hlf-ord:7050
channel-proposal-update.sh mychannel orderer-hlf-ord:7050 ./proposal.pb
```

### Chaincode instanciate
```
chaincode-instantiate.sh mychannel orderer-hlf-ord:7050 mycc 1.0 MyPeer1MSP
```

### Chaincode upgrade
```
peer chaincode upgrade -C $CHANNEL_ID -n $CHAINCODE_NAME -v $CHAINCODE_VERSION -c '{"Args":["init"]}' -P "OR('MyPeer1MSP.member', 'MyPeer2MSP.member')" -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt
```

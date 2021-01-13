# Changelog


# 6.0.0

Application channel chaincodes have now a [sequence](https://hyperledger-fabric.readthedocs.io/en/release-2.2/commands/peerlifecycle.html?highlight=sequence) field.

Example:

```yaml
chaincodes:
  - name: mycc
    address: network-org-1-peer-1-hlf-k8s-chaincode-mycc.org-1
    port: 7052
    version: "1.0"
    image:
      repository: substrafoundation/substra-chaincode
      tag: 0.1.1
      pullPolicy: IfNotPresent


appChannels:
- channelName: mychannel
  chaincodes:
  - name: mycc
    policy: "OR('MyOrg1MSP.member','MyOrg2MSP.member')"
    version: "1.0"
    sequence: "1"
```

# 5.0.0

Chaincode properties have been moved from `appChannels[].chaincodes[]` to `chaincodes[]`, which the exception of the `policy`, `name` and `version` fields.

Example:

```yaml
chaincodes:
  - name: mycc
    address: network-org-1-peer-1-hlf-k8s-chaincode-mycc.org-1
    port: 7052
    version: "1.0"
    image:
      repository: substrafoundation/substra-chaincode
      tag: 0.1.1
      pullPolicy: IfNotPresent


appChannels:
- channelName: mychannel
  chaincodes:
  - name: mycc
    policy: "OR('MyOrg1MSP.member','MyOrg2MSP.member')"
    version: "1.0"
```

## 4.0.0


Peer use now couchdb as default instead of goleveldb
Orderer is now under etcdraft type and not solo anymore
Policies are mandatory and need to be set for : SystemChannel, Application and Channel


hlf-k8s appChannels field expose now :
 - application policies
 - channel policies
 - chaincodes, which is not isolated anymore

Rename images from hlf-k8s to fabric-tools and fabric-ca-tools

/!\ As we use TLS for chaincode and peer communications, you need to add chaincode fqdn in the csrHost of the CA enrollement

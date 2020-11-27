# Upgrade

## 4.0.0

- Peer use now couchdb as default instead of goleveldb
- Orderer is now under etcdraft type and not solo anymore
- Policies are mandatory and need to be set for : SystemChannel, Application and Channel
- Rename images from hlf-k8s to fabric-tools and fabric-ca-tools

The `chaincodes` field now exposes the list of chaincodes to be installed on the peer

For each channel, the `appChannels[].chaincodes` field now exposes:
 - the name of the chaincode(s) to install
 - the application policy

/!\ As we use TLS for chaincode and peer communications, you need to add chaincode fqdn in the csrHost of the CA enrollement

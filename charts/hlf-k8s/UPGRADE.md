# Changelog


## 4.0.0


Peer use now couchdb as default instead of goleveldb
Orderer is now under etcdraft type and not solo anymore
Policies are mandatory and need to be set for : SystemChannel, Application and Channel


hlf-k8s appChannels field expose now :
 - application policies
 - channel policies
 - chaincodes, which is not isolated anymore

Rename images from hlf-k8s to fabric-tools and fabric-tools-ca

/!\ As we use TLS for chaincode and peer communications, you need to add chaincode fqdn in the csrHost of the CA enrollement

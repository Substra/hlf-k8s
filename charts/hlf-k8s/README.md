# HLF k8s

HLF-k8s is a network of [Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/en/release-2.2/) orderers and peers, forming a permissioned blockchain.

The network is formed of multiple nodes (peers/orderers). Each node is installed using the same chart, but with different configurations (see [Usage](#usage)).

Hlf-k8s runs Hyperledger Fabric v2.x

## Prerequisites

- Kubernetes 1.16+

## Changelog

See [CHANGELOG.md](./CHANGELOG.md)

## Configuration

The following table lists the configurable parameters of the hlf-k8s chart and default values.

| Parameter                          | Description                                     | Default                                                    |
| ---------------------------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| **Peer** |  |  |
| `hlf-peer.enabled` | If true, a HLF Peer will be installed | `true` |
| `hlf-peer.peer.mspID` | ID of MSP the Peer belongs to | `Org1MSP` |
| `hlf-peer.discover-monitor.enabled` | If true, create a discover monitor pod (see [Monitoring pods](#monitoring-pods)) | `false` |
| `hlf-peer.peer.gossip.externalEndpoint` | HLF peer gossip external endpoint | `""` |
| `hlf-peer.peer.databaseType` | Database type to use (goleveldb or CouchDB) | `CouchDB` |
| `hlf-peer.peer.couchdbSecret` | Secret holding the couchdb credentials | `cdb-peer-hlf-k8s-couchdb-credentials` |
| `hlf-peer.peer.couchdbInstance` | CouchDB chart name to use cdb-peer | `cdb-peer` |
| `hlf-peer.host` | The Peers's host | `peer-hostname` |
| `hlf-peer.port` | The Peers's port | `7051` |
| `hlf-peer.peer.docker.enabled` | If true, mount host docker socket in the peer container | `false` |
| `hlf-peer.ingress.enabled` | If true, Ingress will be created for the Peer | `false` |
| `hlf-peer.ingress.annotations` | Peer ingress annotations | `nil` |
| `hlf-peer.ingress.tls` | Peer ingress TLS configuration | `nil` |
| `hlf-peer.ingress.hosts` | Peer ingress hosts | `nil` |
| `hlf-peer.persistence.enabled` | If true, enable persistence for the Peer | `true` |
| `hlf-peer.persistence.size` | Size of data volume | `10Gi` |
| `hlf-peer.persistence.storageClass` | Storage class of backing PVC | `nil` |
| `appChannels` | The application channels to create | `[{channelName: mychannel}]` |
| `appChannels[].channelName` | The name of the application channel. Must be alphanumerical (9 characters max.) | `nil` |
| `appChannels[].organizations` | The organizations to add to the application channel. See [Add an organization to the application channel](#add-an-organization-to-the-application-channel). | `[]` |
| `appChannels[].proposalOrganizations` | The organizations to fetch signed application channel update proposals from. | `[]` |
| `appChannels[].channelPolicies` | This value overrides the default HLF channel policy. | (defined in values.yaml) |
| `appChannels[].appPolicies` | This value overrides the default HLF application policy. | (defined in values.yaml) |
| `appChannels[].chaincodes` | The chaincodes to install on the Peer. See [Install a chaincode](#install-a-chaincode). | `[]` |
| `appChannels[].chaincodes[].name` | The name of the chaincode | `nil` |
| `appChannels[].chaincodes[].version` | The chaincode version | `nil` |
| `appChannels[].chaincodes[].sequence` | The chaincode sequence | `nil` |
| `appChannels[].chaincodes[].policy` | The chaincode policy for this channel | `nil` |
| `appChannels[].ingress.enabled` | If true, Ingress will be created for this application channel operator. | `false` |
| `appChannels[].ingress.annotations` | Application channel operator ingress annotations | `nil` |
| `appChannels[].ingress.tls` | Application channel operator ingress TLS configuration | `nil` |
| `appChannels[].ingress.hosts` | Application channel operator ingress hosts | `nil` |
| `appChannels[].ingress.ingressClassName` | Ingress class that will be used for the ingress | `nil` |
| `appChannels[].ingress.pathType` | Ingress path type | `nil` |
| `chaincodes` | The chaincodes to install on the peer | `[]` |
| `chaincodes[].name` | The name of the chaincode | `nil` |
| `chaincodes[].version` | The chaincode version | `nil` |
| `chaincodes[].address` | The URL to the chaincode service | `nil` |
| `chaincodes[].port` | The port to the chaincode service | `nil` |
| `chaincodes[].logLevel` | The log level for the chaincode process | `nil`|
| `chaincodes[].image.repository` | `chaincode` image repository | `nil` |
| `chaincodes[].image.tag` | `chaincode` image tag | `nil` |
| `chaincodes[].image.pullPolicy` | Image pull policy | `nil` |
| `chaincodes[].image.pullImageSecret` | Image pull secret name | `nil` |
| `chaincodes[].init.image.repository` | optional chaincode's `initContainer` image repository | `nil` |
| `chaincodes[].init.image.tag` | optional chaincode's `initContainer` image tag | `nil` |
| `configOperator.ingress.enabled` | If true, Ingress will be created for the config operator. | `false` |
| `configOperator.ingress.annotations` | Config operator ingress annotations | `nil` |
| `configOperator.ingress.tls` | Config operator ingress TLS configuration | `nil` |
| `configOperator.ingress.hosts` | Config operator ingress hosts | `nil` |
| `configOperator.ingress.ingressClassName` | Ingress class that will be used for the ingress | `nil` |
| `configOperator.ingress.pathType` | Ingress path type | `ImplementationSpecific` |
| `genesis.generate` | If true, generate a HLF genesis block and populate the `secrets.genesis` secret | `true` |
| **Orderer** |  |  |
| `hlf-ord.enabled` | If true, a HLF Orderer will be installed | `false` |
| `hlf-ord.host` | The hostname for the Orderer | `orderer-hostname` |
| `hlf-ord.port` | The Orderer's port | `7050` |
| `hlf-ord.ord.mspID` | ID of MSP the Orderer belongs to | `MyOrdererMSP` |
| `hlf-ord.monitor.enabled` | If true, create a monitor pod (see [Monitoring pods](#monitoring-pods)) | `false` |
| `hlf-ord.ingress.enabled` | If true, Ingress will be created for the Orderer | `nil` |
| `hlf-ord.ingress.annotations` | Orderer ingress annotations | `nil` |
| `hlf-ord.ingress.tls` | Orderer ingress TLS configuration | `nil` |
| `hlf-ord.ingress.hosts` | Orderer ingress hosts | `nil` |
| `hlf-ord.persistence.enabled` | If true, enable persistence for the Orderer | `true` |
| `hlf-ord.persistence.size` | Size of data volume | `10Gi` |
| `hlf-ord.persistence.storageClass` | Storage class of backing PVC | `nil` |
| `systemChannel.name` | The name of the system channel | `systemchannel` |
| `systemChannel.organizations` | The organizations to add to the system channel. See [Add an organization to the system channel](#add-an-organization-to-the-system-channel). | `[]` |
| **Common / Other** |  |  |
| `fabric-tools.image.repository` | `fabric-tools` image repository | `gcr.io/connect-314908/fabric-tools` |
| `fabric-tools.image.tag` | `fabric-tools` image tag | `0.2.2` |
| `fabric-tools.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `fabric-tools.image.pullImageSecret` | Image pull secret name | nil |
| `nodeSelector` | Node labels for pod assignment | `{}` |
| `tolerations` | Toleration labels for pod assignment | `[]` |
| `affinity` | Affinity settings for pod assignment | `{}` |
| `organization.id` | The organization id | `MyOrganizationMSP` |
| `organization.name` | The organization name | `MyOrganization` |
| `enrollments.creds` | The users to enroll with the CA | `[]` |
| `enrollments.csrHost` | The value to pass to `--csr.hosts` when enrolling users to the CA | `service-hostname` |
| `hlf-ca.caName` | Name of CA | `rca` |
| `hlf-ca.scheme` | CA scheme | `http` |
| `hlf-ca.host` | CA host | `ca-hostname` |
| `hlf-ca.port` | CA port | `7054` |
| `hlf-ca.orderer.scheme` | Orderer's CA scheme | `http` |
| `hlf-ca.orderer.host` | Orderer's CA host | `orderer-ca-hostname` |
| `hlf-ca.orderer.port` | Orderer's CA port | `7054` |
| `hlf-ca.persistence.enabled` | If true, enable persistence for the CA | `true` |
| `hlf-ca.persistence.size` | Size of data volume | `5Gi` |
| `hlf-ca.persistence.storageClass` | Storage class of backing PVC | `nil` |
| `couchdb.image.repository` | `couchdb` image repository | `hyperledger/fabric-couchdb` |
| `couchdb.image.tag`| `couchdb` image tag | `0.4.21` |
| `couchdb.image.pullPolicy`| Image pull policy| `IfNotPresent` |
| `couchdb.service.port`| TCP port   | `5984` |
| `couchdb.service.type`| K8S service type exposing ports, e.g. `ClusterIP`| `ClusterIP` |
| `couchdb.persistence.size`| Size of data volume (adjust for production!) | `10Gi` |
| `couchdb.persistence.storageClass`| Storage class of backing PVC | `default` |
| `couchdb.couchdbUsername`| Username for CouchDB| `couchdb` |
| `couchdb.couchdbPassword`| Password for CouchDB  | `couchdbpwd` |
| `privateCa.enabled` | if true, use a private CA | `false` |
| `privateCa.configMap.name` | The name of the ConfigMap containing the private CA certificate | `private-ca` |
| `privateCa.configMap.fileName` | The CA certificate filename within the ConfigMap | `private-ca.crt` |
| `hooks.deleteSecrets.enabled` | If true, the HLF crypto materials secrets created by the chart will be automatically deleted when the chart is uninstalled | `true` |
| `hooks.deleteCCIDSecrets.enabled` | If true, the chaincode ccid secrets created by the chart will be automatically deleted when the chart is uninstalled | `true` |
| `hooks.serviceAccount.name` | `serviceAccount` used for the post-delete hooks, must be able to delete secrets | `""` |
| `hooks.serviceAccount.namespace` | namespace of the `serviceAccount` used for the post-delete hook, this will define the namespace in which the hook job run (if unset it will be replaced by the release namespace) | `""`
| `toolbox.enabled` | If true, a "toolbox" pod will be created with pre-installed utilities and certificates | `false` |


## Usage

### Basic example

For an example using 1 orderer and 2 peers, see the [skaffold.yaml](../../skaffold.yaml) file.

### Install a chaincode

Install a chaincode on a peer using the following values.

On a peer:

```yaml
chaincodes:
  - name: mycc
    version: "1.0"
    address: "chaincode-org-1-substra-chaincode-chaincode.org-1.svc.cluster.local"
    port: "7052"
    image:
      repository: substra/orchestrator-chaincode
      tag: 0.3.0
      pullPolicy: IfNotPresent

appChannels:
  - channelName: mychannel
    chaincodes:
      - name: mycc
        policy: "OR('Org1MSP.member','Org2MSP.member')"
        version: "1.0"
```


### Test hlf-k8s with your own chaincode


Example with substra/orchestrator

```bash
git clone git@github.com:Substra/orchestrator.git
```

Make your edits to substra/orchestrator.

Then build the image:

```bash
docker build -f docker/orchestrator-chaincode/Dockerfile -t substra/orchestrator-chaincode:dev .
docker build -f docker/orchestrator-chaincode-init/Dockerfile -t substra/orchestrator-chaincode-init:dev .
```

*Note: If you use minikube, you need to run `eval $(minikube -p minikube docker-env)` first*


Finally, modify deployment values to use your chaincode image:

For instance with `substra/orchestrator-chaincode:my-tag`
```yaml
chaincodes:
- address: network-org-1-peer-1-hlf-k8s-chaincode-mycc.org-1.svc.cluster.local
  name: mycc
  port: 7052
  version: "1.0"
  image:
    repository: substra/orchestrator-chaincode
    tag: my-tag
```

### Add an organization to the system channel

Adding an organization to the system channel allows it to adminstrate application channels.

To add organizations to the system channel, enable the orderer and set the `systemChannel.organizations` value:

```yaml
hlf-ord:
   enabled: true
systemChannel:
   organizations:
      - org: MyOrg1
        configUrl: peer.org-1.com/config/configOrg.json
      - org: MyOrg2
        configUrl: peer.org-2.com/config/configOrg.json
```

On peers, expose the `/config/` route using the  `configOperator.ingress` key.

### Add an organization to the application channel

#### `MAJORITY` policy (default)

With the default application channel policty (`MAJORITY`), peers need to request approval from one another before they can add an organization to the application channel.

This is done by configuring peers like so:


```yaml
hlf-peer:
   enabled: true

# Add `MyOrg1` and `MyOrg2` to the application channel
appChannels:
- channelName: mychannel
  organizations:
  - org: MyOrg1
    configUrl: peer.org-1.com/config/configOrgWithAnchors.json
  - org: MyOrg2
    configUrl: peer.org-2.com/config/configOrgWithAnchors.json
    [...]
  proposalOrganizations:
  - org: MyOrg1
    proposalServerUrl: peer.org-1.com/mychannel/proposal/
  - org: MyOrg2
    proposalServerUrl: peer.org-2.com/mychannel/proposal/
    [...]
  # Expose this peer's /mychannel/proposal route
  ingress:
    enabled: true
    hosts:
    - { host: peer.org-1, paths: ["/mychannel/proposal"] }

# Expose this peer's /config route
configOperator:
  ingress:
    enabled: true
    hosts:
    - { host: peer.org-1, paths: ["/config"] }
```

A majority of peers need to be configured with the above

#### Other policy (e.g. `ANY` policy)

The default Hyperledger Fabric application channel policy is `MAJORITY`.  This means a node can only be added to the application channel if a majority of the peers already present in the channel agree.

Use the `appChannel.policy` key to override the default application channel policy.

For instance, you can configure the application channel with an `ANY` policy.

Orderer configuration:

```yaml
appChannels:
- channelName: mychannel
  channelPolicies: |
     Readers:
           Type: ImplicitMeta
           Rule: "ANY Readers"
     Writers:
           Type: ImplicitMeta
           Rule: "ANY Writers"
     Admins:
           Type: ImplicitMeta
           Rule: "ANY Admins"
```

With this configuration, any peer is allowed to add _all_ the organizations to the application channel, without requiring approval for the other peers.

Peer configuration (any peer):

```yaml
appChannels:
- channelName: mychannel
  organizations:
  - org: MyOrg1
    configUrl: peer.org-1.com/config/configOrgWithAnchors.json
  - org: MyOrg2
    configUrl: peer.org-2.com/config/configOrgWithAnchors.json
```

On each peer, expose the `config` route using `configOperator.ingress`.


### Monitoring pods

Two types of monitoring pods are offered to facilitate troubleshooting. They periodically poll and display information about the system and application channels. Check the pod's log to see the relevant information.

- **monitor pod** shows the orgs that **have been added** to an application channel (by a member of the system channel).
- **discover-monitor pod** shows the orgs that **have have joined** a channel **and are online**

Note that the monitor pod also shows the orgs that are part of the **system channel**.

To enable the **monitor pod**, on the orderer:

```yaml
monitor:
   enabled: true
```

To enable the **discover monitor pod**, on the peer:

```yaml
discover-monitor:
   enabled: true
```

### Installing behind an ingress

As Hyperledger Fabric uses mutual TLS to authenticate between components, you need the ingress to keep the information encrypted when it sends it to the peer or orderer.
In order to achieve this for example with an nginx ingress you need to set the following value in your ingress controller configuration:
```yaml
controller.extraArgs.enable-ssl-passthrough: ""
```


## Additional resources

- [Hyperledger Fabric documentation](https://hyperledger-fabric.readthedocs.io/en/release-1.4/)

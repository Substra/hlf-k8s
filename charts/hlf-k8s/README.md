# HLF k8s

HLF-k8s is a network of [Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/en/release-1.4) orderers and peers, forming a permissioned blockchain.

The network is formed of multiple nodes (peers/orderers). Each node is installed using the same chart, but with different configurations (see [Usage](#Usage)).

Hlf-k8s runs Hyperledger Fabric v1.4.

## Prerequisites

- Kubernetes 1.14+

## Configuration

The following table lists the configurable parameters of the hlf-k8s chart and default values.

| Parameter                          | Description                                     | Default                                                    |
| ---------------------------------- | ------------------------------------------------ | ---------------------------------------------------------- |
| **Peer** |  |  |
| `peer.enabled` | If true, a HLF Peer will be installed | `true` |
| `peer.peer.mspID` | ID of MSP the Peer belongs to | `Org1MSP` |
| `peer.peer.gossip.externalEndpoint` | HLF peer gossip external endpoint | `""` |
| `peer.ingress.enabled` | If true, Ingress will be created for the Peer | `false` |
| `peer.ingress.annotations` | Peer ingress annotations | (undefined) |
| `peer.ingress.tls` | Peer ingress TLS configuration | (undefined) |
| `peer.ingress.hosts` | Peer ingress hosts | (undefined) |
| `peer.persistence.enabled` | If true, enable persistence for the Peer | `false` |
| `peer.persistence.size` | Size of data volume | (undefined) |
| `peer.persistence.storageClass` | Storage class of backing PVC | (undefined) |
| `chaincodes` | The chaincodes to install on the Peer. See [Install a chaincode](#Install_a_chaincode). | `[]` |
| `appChannel.name` | The name of the application channel | `mychannel` |
| `appChannel.organizations` | The organizations to add to the application channel. See [Add an organization to the application channel](#Add_an_organization_to_the_application_channel). | `[]` |
| `appChannel.proposalOrganizations` | The organizations to fetch signed application channel update proposals from. | `[]` |
| `appChannel.chaincodePolicy` | The chaincode policy | `"OR('Org1MSP.member','Org2MSP.member')"` |
| `appChannel.chaincodeName` | The chaincode name | (undefined) |
| `appChannel.chaincodeVersion` | The chaincode version | (undefined) |
| `appChannel.policies` | This value, if set, will override the default HLF application channel policy. See [Add an organization to the application channel](#Add_an_organization_to_the_application_channel). | (undefined) |
| `configOperator.ingress.enabled` | If true, Ingress will be created for the config operator. | `false` |
| `configOperator.ingress.annotations` | Config operator ingress annotations | (undefined) |
| `configOperator.ingress.tls` | Config operator ingress TLS configuration | (undefined) |
| `configOperator.ingress.hosts` | Config operator ingress hosts | (undefined) |
| `applicationChannelOperator.ingress.enabled` | If true, Ingress will be created for the application channel operator. | `false` |
| `applicationChannelOperator.ingress.annotations` | Application channel operator ingress annotations | (undefined) |
| `applicationChannelOperator.ingress.tls` | Application channel operator ingress TLS configuration | (undefined) |
| `applicationChannelOperator.ingress.hosts` | Application channel operator ingress hosts | (undefined) |
| **Orderer** |  |  |
| `orderer.enabled` | If true, a HLF Orderer will be installed | `false` |
| `orderer.host` | The hostname for the Orderer | `orderer-hostname` |
| `orderer.ord.mspID` | ID of MSP the Orderer belongs to | `MyOrdererMSP` |
| `orderer.monitor.enabled` | If true, create a monitor pod (see [Monitor pod](#Monitor_pod)) | `false` |
| `orderer.ingress.enabled` | If true, Ingress will be created for the Orderer | (undefined) |
| `orderer.ingress.annotations` | Orderer ingress annotations | (undefined) |
| `orderer.ingress.tls` | Orderer ingress TLS configuration | (undefined) |
| `orderer.ingress.hosts` | Orderer ingress hosts | (undefined) |
| `orderer.persistence.enabled` | If true, enable persistence for the Orderer | `false` |
| `orderer.persistence.size` | Size of data volume | (undefined) |
| `orderer.persistence.storageClass` | Storage class of backing PVC | (undefined) |
| `systemChannel.name` | The name of the system channel | `systemchannel` |
| `systemChannel.organizations` | The organizations to add to the system channel. See [Add an organization to the system channel](#Add_an_organization_to_the_system_channel). | `[]` |
| **Common / Other** |  |  |
| `image.repository` | `hlf-k8s` image repository | `substrafoundation/hlf-k8s` |
| `image.tag` | `hlf-k8s` image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `nodeSelector` | Node labels for pod assignment | `{}` |
| `tolerations` | Toleration labels for pod assignment | `[]` |
| `affinity` | Affinity settings for pod assignment | `{}` |
| `organization.id` | The organization id | `MyOrganizationMSP` |
| `organization.name` | The organization name | `MyOrganization` |
| `enrollments.creds` | The users to enroll with the CA | `[]` |
| `enrollments.csrHost` | The value to pass to `--csr. hosts` when enrolling users to the CA | `service-hostname` |
| `ca.caName` | Name of CA | `rca` |
| `ca.scheme` | CA scheme | `http` |
| `ca.host` | CA host | `ca-hostname` |
| `ca.port` | CA port | `7054` |
| `ca.orderer.scheme` | Orderer's CA scheme | `http` |
| `ca.orderer.host` | Orderer's CA host | `orderer-ca-hostname` |
| `ca.orderer.port` | Orderer's CA port | `7054` |
| `ca.persistence.enabled` | If true, enable persistence for the CA | `false` |
| `ca.persistence.size` | Size of data volume | (undefined) |
| `ca.persistence.storageClass` | Storage class of backing PVC | (undefined) |
| `nginx-ingress.enabled` | If true, an nginx Ingress controller will be created | `false` |
| `nginx-ingress.controller.nginx-ingress.extraArgs` | Additional controller arguments | `enable-ssl-passthrough: ""` |
| `privateCa.enabled` | if true, use a private CA | `false` |
| `privateCa.configMap.name` | The name of the ConfigMap containing the private CA certificate | `private-ca` |
| `privateCa.configMap.fileName : ` | The CA certificate filename within the ConfigMap | `private-ca.crt` |


## Usage

### Basic example

For an example using 1 orderer and 2 peers, see the [skaffold.yaml](../../skaffold.yaml) file.

### Install a chaincode

Install a chaincode on a peer using the following values.

On a peer:

```yaml
chaincodes:
  - name: mycc     # Chaincode name
    version: "1.0" # Chaincode version
    # Chaincode source code archive URL
    src: https://github.com/SubstraFoundation/substra-chaincode/archive/0.0.2.tar.gz
```

### Add an organization to the system channel

Adding an organization to the system channel allows it to adminstrate application channels.

To add organizations to the system channel, enable the orderer and set the `systemChannel.organizations` value:

```yaml
orderer:
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
peer:
   enabled: true

# Add `MyOrg1` and `MyOrg2` to the application channel
appChannel:
   organizations:
      - org: MyOrg1
        configUrl: peer.org-1.com/config/configOrgWithAnchors.json
      - org: MyOrg2
        configUrl: peer.org-2.com/config/configOrgWithAnchors.json
      [...]
   proposalOrganizations:
      - org: MyOrg1
      proposalServerUrl: peer.org-1.com/proposal/
      - org: MyOrg2
      proposalServerUrl: peer.org-2.com/proposal/
      [...]

# Expose this peer's /config route
configOperator:
  ingress:
    enabled: true
    hosts:
      - { host: peer.org-1, paths: ["/config"] }

# Expose this peer's /proposal route
applicationChannelOperator:
  ingress:
    enabled: true
    hosts:
      - { host: peer.org-1, paths: ["/proposal"] }

```

A majority of peers need to be configured with the above

#### Other policy (e.g. `ANY` policy)

The default Hyperledger Fabric application channel policy is `MAJORITY`.  This means a node can only be added to the application channel if a majority of the peers already present in the channel agree.

Use the `appChannel.policy` key to override the default application channel policy.

For instance, you can configure the application channel with an `ANY` policy.

Orderer configuration:

```yaml
appChannel:
   policies: |
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
appChannel:
   organizations:
      - org: MyOrg1
        configUrl: peer.org-1.com/config/configOrgWithAnchors.json
      - org: MyOrg2
        configUrl: peer.org-2.com/config/configOrgWithAnchors.json
```

On each peer, expose the `config` route using `configOperator.ingress`.


### Monitor pod

The monitor pod periodically polls and displays the list of organizations that have joined the system channel and the application channel.

It is a convenience feature which facilitates troubleshooting.

To enable it, on the orderer:

```
monitor:
   enabled: true
```

Check the pod's logs to get the list of organizations currently present in each channel.


## Additional resources

- [Hyperledger Fabric documentation](https://hyperledger-fabric.readthedocs.io/en/release-1.4/)

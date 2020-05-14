# HLF k8s

HLF-k8s is a network of [Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/en/release-1.4) orderers and peers, forming a permissioned blockchain.

The network is formed of multiple nodes (peers/orderers). Each node is installed using the same chart, but with different configurations (see [Usage](#usage)).

Hlf-k8s runs Hyperledger Fabric v1.4.

## Prerequisites

- Kubernetes 1.14+

## Configuration

The following table lists the configurable parameters of the hlf-k8s chart and default values.

| Parameter                          | Description                                     | Default                                                    |
| ---------------------------------- | ------------------------------------------------ | ---------------------------------------------------------- |
| **Peer** |  |  |
| `hlf-peer.enabled` | If true, a HLF Peer will be installed | `true` |
| `hlf-peer.peer.mspID` | ID of MSP the Peer belongs to | `Org1MSP` |
| `hlf-peer.peer.gossip.externalEndpoint` | HLF peer gossip external endpoint | `""` |
| `hlf-peer.host` | The Peers's host | `peer-hostname` |
| `hlf-peer.port` | The Peers's port | `7051` |
| `hlf-peer.ingress.enabled` | If true, Ingress will be created for the Peer | `false` |
| `hlf-peer.ingress.annotations` | Peer ingress annotations | (undefined) |
| `hlf-peer.ingress.tls` | Peer ingress TLS configuration | (undefined) |
| `hlf-peer.ingress.hosts` | Peer ingress hosts | (undefined) |
| `hlf-peer.persistence.enabled` | If true, enable persistence for the Peer | `false` |
| `hlf-peer.persistence.size` | Size of data volume | (undefined) |
| `hlf-peer.persistence.storageClass` | Storage class of backing PVC | (undefined) |
| `chaincodes` | The chaincodes to install on the Peer. See [Install a chaincode](#install-a-chaincode). | `[]` |
| `chaincodes[].name` | The name of the chaincode | (undefined) |
| `chaincodes[].version` | The chaincode version | (undefined) |
| `chaincodes[].src` | The URL to a chaincode archive (.tar.gz) | (undefined) |
| `chaincodes[].hostPath` | A host path containing the chaincode source code | (undefined) |
| `chaincodes[].configMap.name` | The name of a ConfigMap containing the chaincode source code (tar.gz) | (undefined) |
| `chaincodes[].configMap.fileName` | The name of the archive within the ConfigMap | (undefined) |
| `appChannel.name` | The name of the application channel | `mychannel` |
| `appChannel.organizations` | The organizations to add to the application channel. See [Add an organization to the application channel](#add-an-organization-to-the-application-channel). | `[]` |
| `appChannel.proposalOrganizations` | The organizations to fetch signed application channel update proposals from. | `[]` |
| `appChannel.chaincodePolicy` | The chaincode policy | `OR(`<br>`'Org1MSP.member',`<br>`  'Org2MSP.member')` |
| `appChannel.chaincodeName` | The chaincode name | (undefined) |
| `appChannel.chaincodeVersion` | The chaincode version | (undefined) |
| `appChannel.policies` | This value, if set, will override the default HLF application channel policy. See [Add an organization to the application channel](#add-an-organization-to-the-application-channel). | (undefined) |
| `configOperator.ingress.enabled` | If true, Ingress will be created for the config operator. | `false` |
| `configOperator.ingress.annotations` | Config operator ingress annotations | (undefined) |
| `configOperator.ingress.tls` | Config operator ingress TLS configuration | (undefined) |
| `configOperator.ingress.hosts` | Config operator ingress hosts | (undefined) |
| `applicationChannelOperator.ingress`<br>&nbsp;&nbsp;&nbsp;&nbsp;`.enabled` | If true, Ingress will be created for the application channel operator. | `false` |
| `applicationChannelOperator.ingress`<br>&nbsp;&nbsp;&nbsp;&nbsp;`.annotations` | Application channel operator ingress annotations | (undefined) |
| `applicationChannelOperator.ingress`<br>&nbsp;&nbsp;&nbsp;&nbsp;`.tls` | Application channel operator ingress TLS configuration | (undefined) |
| `applicationChannelOperator.ingress`<br>&nbsp;&nbsp;&nbsp;&nbsp;`.hosts` | Application channel operator ingress hosts | (undefined) |
| `hooks.uninstallChaincode.enabled` | If true, the chaincode will be automatically uninstalled when the chart is uninstalled | `true` |
| **Orderer** |  |  |
| `hlf-ord.enabled` | If true, a HLF Orderer will be installed | `false` |
| `hlf-ord.host` | The hostname for the Orderer | `orderer-hostname` |
| `hlf-ord.ord.mspID` | ID of MSP the Orderer belongs to | `MyOrdererMSP` |
| `hlf-ord.monitor.enabled` | If true, create a monitor pod (see [Monitor pod](#monitor-pod)) | `false` |
| `hlf-ord.ingress.enabled` | If true, Ingress will be created for the Orderer | (undefined) |
| `hlf-ord.ingress.annotations` | Orderer ingress annotations | (undefined) |
| `hlf-ord.ingress.tls` | Orderer ingress TLS configuration | (undefined) |
| `hlf-ord.ingress.hosts` | Orderer ingress hosts | (undefined) |
| `hlf-ord.persistence.enabled` | If true, enable persistence for the Orderer | `false` |
| `hlf-ord.persistence.size` | Size of data volume | (undefined) |
| `hlf-ord.persistence.storageClass` | Storage class of backing PVC | (undefined) |
| `systemChannel.name` | The name of the system channel | `systemchannel` |
| `systemChannel.organizations` | The organizations to add to the system channel. See [Add an organization to the system channel](#add-an-organization-to-the-system-channel). | `[]` |
| **Common / Other** |  |  |
| `image.repository` | `hlf-k8s` image repository | `substrafoundation/hlf-k8s` |
| `image.tag` | `hlf-k8s` image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `nodeSelector` | Node labels for pod assignment | `{}` |
| `tolerations` | Toleration labels for pod assignment | `[]` |
| `affinity` | Affinity settings for pod assignment | `{}` |
| `organization.id` | The organization id | `MyOrganizationMSP` |
| `organization.name` | The organization name | `MyOrganization` |
| `hlf-ord.host` | The Orderer's host | `orderer-hostname` |
| `hlf-ord.port` | The Orderer's port | `7050` |
| `enrollments.creds` | The users to enroll with the CA | `[]` |
| `enrollments.csrHost` | The value to pass to `--csr.hosts` when enrolling users to the CA | `service-hostname` |
| `hlf-ca.caName` | Name of CA | `rca` |
| `hlf-ca.scheme` | CA scheme | `http` |
| `hlf-ca.host` | CA host | `ca-hostname` |
| `hlf-ca.port` | CA port | `7054` |
| `hlf-ca.orderer.scheme` | Orderer's CA scheme | `http` |
| `hlf-ca.orderer.host` | Orderer's CA host | `orderer-ca-hostname` |
| `hlf-ca.orderer.port` | Orderer's CA port | `7054` |
| `hlf-ca.persistence.enabled` | If true, enable persistence for the CA | `false` |
| `hlf-ca.persistence.size` | Size of data volume | (undefined) |
| `hlf-ca.persistence.storageClass` | Storage class of backing PVC | (undefined) |
| `nginx-ingress.enabled` | If true, an nginx Ingress controller will be created | `false` |
| `nginx-ingress.controller.nginx-ingress.extraArgs` | Additional controller arguments | `enable-ssl-passthrough: ""` |
| `privateCa.enabled` | if true, use a private CA | `false` |
| `privateCa.configMap.name` | The name of the ConfigMap containing the private CA certificate | `private-ca` |
| `privateCa.configMap.fileName` | The CA certificate filename within the ConfigMap | `private-ca.crt` |
| `hooks.deleteSecrets.enabled` | If true, the secrets created by the chart will be automatically deleted when the chart is uninstalled | `true` |
| `toolbox.enabled` | If true, a "toolbox" pod will be created with pre-installed utilities and certificates | `false` |


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

You can also provide the chaincode source code using a ConfigMap or a host path (see: [Configuration](#Configuration))

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

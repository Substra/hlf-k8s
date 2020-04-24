# HLF k8s

A deployment of [Hyperledger Fabric](https://www.hyperledger.org/projects/fabric) for the [Substra project](https://github.com/SubstraFoundation/substra).

## Prerequisites

- [kubernetes](https://kubernetes.io/) v1.15
- [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/) v1.18
- [helm](https://github.com/helm/helm) v2.14

## Technical overview

This project runs Hyperledger Fabric v1.4.

- [skaffold.yaml](./skaffold.yaml). The standard deployment used for local development. See also the [Local deployment](#Local_deployment) section.
- Kubernetes resources:
  - orderer
    - **Certificate authority (CA)** Manage identities for the orderer
    - **Orderer** The Hyperledger Fabric orderer
    - **Genesis operator** Create the genesis block required by the orderer
    - **System channel operator** Add organizations to the system channel
  - peer
    - **Certificate authority (CA)** Manage identities for the peer
    - **Peer** The Hyperledger Fabric peer
    - **Enrollment operator** Communicate with the CA to register and enroll an admin user and a regular user
    - **Chaincode operator** Fetch the chaincode source code (see [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode)) and install it on the peer
    - **Application channel operator** Create the application channel. Add organizations to the application channel by signing, exhanging and submitting signed channel update proposals. Expose signed proposals on an HTTP endpoint. Also see [Application channel policy](#Application_channel_policy).
    - **Config operator** Expose the peer's configuration on an HTTP endpoint
    - **Monitor pod** Periodically poll the the system channel and the application channel, and output the list of organizations that have joined each channel. Look at the logs of this pod to have a high-level view of which organizations have successfully joined each channel.

For more details about certificate authorities, peers, orderers, channels, and channel proposals, please refer to the [Hyperledger Fabric documentation](https://hyperledger-fabric.readthedocs.io/en/release-2.0/).

## Local deployment

To deploy hlf-k8s locally, use [skaffold](https://github.com/GoogleContainerTools/skaffold) v1.7+.

The [skaffold.yaml](./skaffold.yaml) file defines a deployment with:

- 1 orderer `MyOrderer`
- 2 organizations: `MyOrg1` and `MyOrg2`

Start the network with

```
skaffold run
```

Once the network is started, the two organizations `MyOrg1` and `MyOrg` are added to the system channel, and then to the application channel. See the [Components](#Components) section for more details.

### Custom chaincode

By default, the `skaffold run` command will start a network using the default [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode).

To use a custom chaincode locally, change the `chaincodes.src` values in [`skaffold.yaml`](./skaffold.yaml) to point to your local clone of substra-chaincode, e.g.

- `deploy.helm.realease.name[network-peer-1].setValues.chaincodes[0].src: /home/johndoe/code/substra-chaincode`
- `deploy.helm.realease.name[network-peer-2].setValues.chaincodes[0].src: /home/johndoe/code/substra-chaincode`

The chaincode path must be accessible from your kubernetes cluster:

- On Docker for Mac, go to Settings > File Sharing and make sure the chaincode folder is included in the mounted folders
- On minikube, run `nohup minikube mount <chaincode-absolute-path>:<chaincode-absolute-path> &`


## Application channel policy

 hlf-k8s supports two application channel policies, ANY and MAJORITY.

### ANY

This is the simplest mode. It is used by the default local deployment (see [skaffold.yaml](./skaffold.yaml))

A node can add any another node to the application channel without the need of approval.


### MAJORITY

A node can only be added to the application channel if a majority of the nodes already present in the channel agree.

This agreement is obtained  via the signature of a "proposal". Each node `A` can sign a channel update proposal allowing node `B` to enter the application channel. Proposals are signed by nodes and exposed to other nodes via HTTP endpoints. Nodes request signed proposals from each other over HTTP and add their own signature. Once enough signatures are collected, the channel update proposal is submitted to the orderer. For more information, see the [application channel operator](./charts/hlf-k8s/templates/deployment-application-channel-operator.yaml).

### Other policies

Although ANY and MAJORITY are the two supported and documented application channel policies in hlf-k8s, a custom application channel policy should be achievable through the `appChannel.policy` key in the [values.yaml](./charts/hlf-k8s/values.yaml) file.


## License

This project is developed under the Apache License, Version 2.0 (Apache-2.0), located in the [LICENSE](./LICENSE) file.


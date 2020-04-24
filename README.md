# HLF k8s

A deployment of [Hyperledger Fabric](https://www.hyperledger.org/projects/fabric) for the [Substra project](https://github.com/SubstraFoundation/substra).

## Prerequisites

- [kubernetes](https://kubernetes.io/) v1.15
- [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/) v1.18
- [helm](https://github.com/helm/helm) v2.14

## Technical overview

This project runs Hyperledger Fabric v1.4.

- [skaffold.yaml](./skaffold.yaml). This file descibes the standard deployment used for local development. See also the [Local deployment](#Local_deployment) section.
- Kubernetes resources:
  - [System channel operator](./charts/hlf-k8s/templates/deployment-system-channel-operator.yaml). This operator adds organizations to the system channel.
  - [Application channel operator](./charts/hlf-k8s/templates/deployment-application-channel-operator.yaml). This operator adds organizations to the application channel.
  - [Monitor pod](./charts/hlf-k8s/templates/deployment-monitor.yaml). This pod periodically polls the the system channel and the application channel, and outputs the list of organizations that have joined each channel. You can look at the logs of this pod to have a high-level view of which organizations have successfully joined each channel.

For more details about channels, peers and orderers, please refer to the [Hyperledger Fabric documentation](https://hyperledger-fabric.readthedocs.io/en/release-2.0/).

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

The [monitor pod](./charts/hlf-k8s/templates/deployment-monitor.yaml) periodically polls the the system channel and the application channel, and outputs the list of organizations that have joined each channel. You can look at the logs of this pod to have a high-level view of which organizations have successfully joined each channel.

### Running a custom version of the chaincode

By default, the `skaffold run` command will start a substra network that uses the default [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode).

To use a custom chaincode locally, change the `chaincodes.src` values in [`skaffold.yaml`](./skaffold.yaml) to point to your local clone of the [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode), e.g.

- `deploy.helm.realease.name[network-peer-1].setValues.chaincodes[0].src: /home/johndoe/code/substra-chaincode`
- `deploy.helm.realease.name[network-peer-2].setValues.chaincodes[0].src: /home/johndoe/code/substra-chaincode`

The chaincode path must be accessible from your kubernetes cluster:

- On Docker for Mac, go to Settings > File Sharing and make sure the chaincode folder is included in the mounted folders
- On a running minikube instance, run `nohup minikube mount <chaincode-absolute-path>:<chaincode-absolute-path> &`


## Application channel policy

 hlf-k8s supports two application channel policies, ANY and MAJORITY.

### ANY

This is the simplest mode. It is used by the default local deployment (see [skaffold.yaml](./skaffold.yaml))

A node can add any another node to the application channel without the need of approval.


### MAJORITY

A node can only be added to the application channel if a majority of the nodes already present in the channel agree.

This agreement is obtained  via the signature of a "proposal". Each node `A` can sign a channel update proposal allowing node `B` to enter the application channel. Proposals are signed by nodes and exposed to other nodes via HTTP endpoints. Nodes request signed proposals from each other over HTTP and add their own signature. Once enough signatures are collected, the channel update proposal is submitted to the orderer. For more information, see the [application channel operator](./charts/hlf-k8s/templates/deployment-application-channel-operator.yaml).

### Use a custom policy

Although ANY and MAJORITY are the only two officially supported and documented application channel policies in hlf-k8s, a custom application channel policy should be achievable through the `appChannel.policy` key in the [values.yaml](./charts/hlf-k8s/values.yaml) file.


## License

This project is developed under the Apache License, Version 2.0 (Apache-2.0), located in the [LICENSE](./LICENSE) file.


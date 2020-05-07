# HLF k8s

HLF-k8s is a network of [Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/en/release-1.4) orderers and peers forming a permissioned blockchain.

It is part of the [Substra project](https://github.com/SubstraFoundation/substra).

## Prerequisites

- [kubernetes](https://kubernetes.io/) v1.15
- [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/) v1.18
- [helm](https://github.com/helm/helm) v2.14

## Local install

Use [skaffold](https://github.com/GoogleContainerTools/skaffold) v1.7+.

To start hlf-k8s, run:

```
skaffold run
```

This will deploy hlf-k8s with:

- 1 orderer `MyOrderer`
- 2 organizations: `MyOrg1` and `MyOrg2`

### Install a custom chaincode

By default, the `skaffold run` command will start a network using the default [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode).

To use a custom chaincode locally, replace the `chaincodes.src` fields to `chaincodes.hostPath` in [`skaffold.yaml`](./skaffold.yaml) to point to your local clone of substra-chaincode, e.g.

- `deploy.helm.realease.name[network-peer-1].setValues.chaincodes[0].hostPath: /home/johndoe/code/substra-chaincode`
- `deploy.helm.realease.name[network-peer-2].setValues.chaincodes[0].hostPath: /home/johndoe/code/substra-chaincode`

The chaincode path must be accessible from your kubernetes cluster:

- On Docker for Mac, go to Settings > File Sharing and make sure the chaincode folder is included in the mounted folders
- On minikube, run `nohup minikube mount <chaincode-absolute-path>:<chaincode-absolute-path> &`

### Production install

Please refer to the [helm chart documentation](./charts/hlf-k8s/README.md).


## License

This project is developed under the Apache License, Version 2.0 (Apache-2.0), located in the [LICENSE](./LICENSE) file.


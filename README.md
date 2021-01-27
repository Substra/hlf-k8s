# HLF k8s [![Helm](https://github.com/SubstraFoundation/hlf-k8s/workflows/Helm/badge.svg)](https://github.com/SubstraFoundation/hlf-k8s/actions?query=workflow%3AHelm)

HLF-k8s is a network of [Hyperledger Fabric](https://hyperledger-fabric.readthedocs.io/en/latest/) orderers and peers forming a permissioned blockchain.

It is part of the [Substra project](https://github.com/SubstraFoundation/substra).

## Prerequisites

- [kubernetes](https://kubernetes.io/) v1.16
- [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/) v1.18
- [helm](https://github.com/helm/helm) v3

## Local install

Use [skaffold](https://github.com/GoogleContainerTools/skaffold) v1.14+.

To start hlf-k8s, run:

```
skaffold run
```

This will deploy hlf-k8s with:

- 1 orderer `MyOrderer`
- 2 organizations: `MyOrg1` and `MyOrg2`

### Running a specific version

To deploy locally a specific version of hlf-k8s, the recommended way is the following:
```bash
SUBSTRA_HLF_VERSION=0.0.16
git checkout $SUBSTRA_HLF_VERSION
skaffold deploy --images substrafoundation/fabric-tools:$SUBSTRA_HLF_VERSION --images substrafoundation/fabric-peer:$SUBSTRA_HLF_VERSION
```

## Install a custom chaincode

By default, the `skaffold run` command will start a network using the default [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode) image.

To use a custom chaincode locally, you need to build and replace the `chaincodes.image` fields to use your local image of substra-chaincode.

You can check how to do it in the [helm chart documentation](./charts/hlf-k8s/README.md) in the `Test hlf-k8s with your own chaincode` section

## Production install / Changelog

Please refer to the [helm chart documentation](./charts/hlf-k8s/README.md).

## License

This project is developed under the Apache License, Version 2.0 (Apache-2.0), located in the [LICENSE](./LICENSE) file.

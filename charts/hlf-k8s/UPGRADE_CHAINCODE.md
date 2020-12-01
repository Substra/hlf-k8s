# Chaincode upgrade procedure

## Disclaimer

The guide demonstrates a very simple upgrade process on a test environment.

It should only serve as a first step, to be further expanded upon.

In particular, this guide lacks information about:

- Chaincode approval process for large consortiums (here we only test with 2 orgs)
- Dealing with various chaincode upgrade policies
- Running the init function for the new chaincode

These aspects shall be detailed in future versions of this guide.

## Prepare the upgrade

### Prerequisites

We have a running network with two organizations: `org-1` and `org-2`.

Each organization runs a chaincode `mycc`.

### Build the new chaincode

Let's edit the `substra-chaincode` source code. For this example, we'll just add "FOO" to a log message:

```diff
-logger.Infof("[%s][%s] Args received: '%s'", stub.GetChannelID(), stub.GetTxID()[:10], stub.GetStringArgs())
+logger.Infof("[%s][%s] Args received FOO: '%s'", stub.GetChannelID(), stub.GetTxID()[:10], stub.GetStringArgs())
```

We then build the chaincode docker image  with tag `0.1.2`

```
docker build . -t substrafoundation/substra-chaincode:0.1.2
```

## Upgrade org-1

In `hlf-k8s`, We create a new chaincode version `2.0` corresponding to the `0.1.2` docker tag. We configure `org-1` to use this new chaincode version:


```diff
chaincodes:
  - name: mycc
    address: network-org-1-peer-1-hlf-k8s-chaincode-mycc.org-1
    port: 7052
-    version: "1.0"
+    version: "2.0"
    image:
      repository: substrafoundation/substra-chaincode
-      tag: 0.1.1
+      tag: 0.1.2
      pullPolicy: IfNotPresent

appChannels:
  chaincodes:
  - name: mycc
    policy: "OR('MyOrg1MSP.member','MyOrg2MSP.member')"
-    version: "1.0"
+    version: "2.0"
```

We then run the upgrade:

```
helm upgrade [...]
```

### Pod status


On org-1:

- A new mycc POD starts: `org-1/network-org-1-peer-1-hlf-k8s-chaincode-mycc-86c494dbd5-59ts2`
- Once the POD is ready, the old mycc POD terminates.

On org-22:

- Nothing changes

### Test the upgrade

We run a test command :

```bash
$ ./examples/test-dev-network.sh 2
```

In the org-1 logs mycc POD logs, we see the updated message.

```
[mychannel][4578fcfbfd] Args received FOO: '[queryTraintuples]'
```

In the org-2 mycc POD logs, the message is unchanged:

```
[mychannel][09fd0041a5] Args received: '[queryTraintuples]'
```


## Upgrade org-2

We can follow the same procedure as for org-1


```diff
chaincodes:
  - name: mycc
    address: network-org21-peer-1-hlf-k8s-chaincode-mycc.org-1
    port: 7052
-    version: "1.0"
+    version: "2.0"
    image:
      repository: substrafoundation/substra-chaincode
-      tag: 0.1.1
+      tag: 0.1.2
      pullPolicy: IfNotPresent

appChannels:
  chaincodes:
  - name: mycc
    policy: "OR('MyOrg1MSP.member','MyOrg2MSP.member')"
-    version: "1.0"
+    version: "2.0"
```

Then we run the upgrade

```
helm upgrade [...]
```

Finally, when we run the test command, we can see the new chaincode is active in the chaincode POD logs:

```
[mychannel][6628bd7837] Args received FOO: '[queryTraintuples]'
```

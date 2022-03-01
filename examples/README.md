These tools are presented for local development and documentation purposes only.

They are maintained on a "best effort" policy.

For the officially supported deployment, please refer to the main [skaffold.yaml](../skaffold.yaml) file.

## Updating crypto material

In order to deploy faster, the default deployed example contains pre-generated crypto material.

However, they will expire at some point. The symptom is that the enrollment operator won't start:

```
2022-02-28 15:10:49.227 UTC 0004 PANI [orderer.common.server] loadLocalMSP -> Failed to setup local msp with config: signing identity expired 48h52m49.227068342s ago
```

Fortunately, there is also an example with a proper CA to issue the required certificates:
```
cd 4-orgs-policy-any
skaffold run
```

This should properly deploy a fabric network.
Now, let's retrieve the secrets and update the manifests (in `secrets` directory):

```
kubectl -n orderer get secret hlf-genesis -oyaml > secrets-orderer-genesis.yaml
kubectl -n orderer get secret hlf-cacert hlf-msp-cert-admin hlf-msp-cert-user hlf-msp-key-admin hlf-msp-key-user hlf-tls-admin hlf-tls-user ord-tls-rootcert -oyaml > secrets-orderer.yaml
kubectl -n org-1 get secret hlf-cacert hlf-msp-cert-admin hlf-msp-cert-user hlf-msp-key-admin hlf-msp-key-user hlf-tls-admin hlf-tls-user ord-tls-rootcert -oyaml > secrets-org-1.yaml
kubectl -n org-2 get secret hlf-cacert hlf-msp-cert-admin hlf-msp-cert-user hlf-msp-key-admin hlf-msp-key-user hlf-tls-admin hlf-tls-user ord-tls-rootcert -oyaml > secrets-org-2.yaml
kubectl -n org-3 get secret hlf-cacert hlf-msp-cert-admin hlf-msp-cert-user hlf-msp-key-admin hlf-msp-key-user hlf-tls-admin hlf-tls-user ord-tls-rootcert -oyaml > secrets-org-3.yaml
kubectl -n org-4 get secret hlf-cacert hlf-msp-cert-admin hlf-msp-cert-user hlf-msp-key-admin hlf-msp-key-user hlf-tls-admin hlf-tls-user ord-tls-rootcert -oyaml > secrets-org-4.yaml
```

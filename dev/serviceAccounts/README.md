# K8s manifests

These manifests are only used in the case of a local skaffold deployment.
We need these service accounts because the Helm post-delete hooks we use needs the permission to delete secrets.

If you want to deploy substra using plain helm and want to use the hooks to clean everything you can adapt these manifests to create a serviceAccount with the right permissions in your cluster.

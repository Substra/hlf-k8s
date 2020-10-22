# Changelog


## 4.0.0

- Switched to hyperledger fabric 2.x, update values accoridingly.
- Use couchdb isntead of goleveldb
- Remove docker dependency and add chaincode pod

## 3.0.2

- Added `genesis.generate` (defaults to `true` - behavior unchanged)

## 3.0.1

- Bump `hlf-peer` chart to `v1.6.0`

## 3.0.0

- Switched to Helm3
- Added `hooks.serviceAccount.name` to specify the serviceAccount used by the post-delete hook `<release>-hook-delete-secrets`
- Added `hooks.serviceAccount.namespace` to specify the serviceAccount namespace (this will also set `<release>-hook-delete-secrets` namespace)

## 1.5.0

- `appChannel` changed to `appChannels` (list)
- `appChannel.name` renamed to `appChannels[].channelName`
- `applicationChannelOperator.ingress` moved to `appChannels[].ingress`

# Changelog

# 5.0.0

- Add support for using the same chaincode on multiple channels.
- This changes the structure of the `appChannels` value. Please see [`UPDGRADE.md`](./UPGRADE.md).

## 4.0.0

- Bump hyperledger fabric to 2.x. Please update values accordingly.
- Use couchdb instead of goleveldb
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

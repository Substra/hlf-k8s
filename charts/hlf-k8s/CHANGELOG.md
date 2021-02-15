# Changelog

# 7.0.0
### Changed
- Charts using API v2 now, officially dropping support form Helm v2
### Removed
- Remove `nginx-ingress` dependency

# 6.2.2

- Reduce the delay between each "add organization" operation in the appchannel operator from 5 secs to 1 sec

# 6.2.1
### Fixed
- `jq` does not fail anymore on mspid containing a special character in the chaincode operator.
- The condition to enter the chaincode commit process in the chaincode operator was always true, now we enter only if the chaincode is not already commited.

# 6.2.0

- Set persistence value for each service to true by default

# 6.1.0

- Bug fix chaincode operator if same chaincode is used over multiple channels.
- Fix examples
- Add new example 2 orgs 2 channels 1 chaincode

# 6.0.0

- Add sequence field to the structure of the `appChannels.chaincodes` value. Please see [`UPDGRADE.md`](./UPGRADE.md).

## 5.1.3

### Fixed
- only approve chaincode once

## 5.1.1

### Fixed
- moved `hlf-peer.docker.enabled` to `hlf-peer.peer.docker.enabled` to correctly disable docker socket mount.

## 5.0.0

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

# Changelog

## 10.2.2

### Changed
- Update image versions

## 10.2.1

### Changed
- Updated documentation

## 10.2.0

### Changed
- Update default images to use public substra registry
- Use `latest` tags of fabric-peer and fabric-tools

## 10.1.2

### Changed
- Update chart metadata

## 10.1.1

### Added
- Component annotation for chaincode pods

## 10.0.1

### Removed
- Unused `users` values.

## 10.0.0

### Changed
- Use couchdb chart instead of hlf-couchdb

## 9.1.2

### Changed
- Update chart's logo

## 9.1.1

### Added
- Support for 1.19.x pre-releases

## 9.1.0

### Added
- Support for chaincode init containers

## 9.0.0

### Added
- Support for Kubernetes 1.22

### Removed
- Support for Kubernetes versions inferior to 1.19

## 8.0.0
### Added
- pullImageSecret on fabric-tools and chaincode images
- Update `hlf-peer` chart to 3.2.0

### Breaking changes
- add `hlf-peer.peer.couchdbSecret` to make the value explicit

## 7.1.0
### Changed
- Update HLF images to 2.4
### Removed
- Remove `fabric-ca-tools` dependency and replace it by `fabric-tools`

## 7.0.1
### Fixed
- The application channel operator doesn't misbehave anymore when a peer joins 2 channels with overlapping names

## 7.0.0
### Changed
- Charts using API v2 now, officially dropping support form Helm v2
### Removed
- Remove `nginx-ingress` dependency

## 6.2.2

- Reduce the delay between each "add organization" operation in the appchannel operator from 5 secs to 1 sec

## 6.2.1
### Fixed
- `jq` does not fail anymore on mspid containing a special character in the chaincode operator.
- The condition to enter the chaincode commit process in the chaincode operator was always true, now we enter only if the chaincode is not already commited.

## 6.2.0

- Set persistence value for each service to true by default

## 6.1.0

- Bug fix chaincode operator if same chaincode is used over multiple channels.
- Fix examples
- Add new example 2 orgs 2 channels 1 chaincode

## 6.0.0

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

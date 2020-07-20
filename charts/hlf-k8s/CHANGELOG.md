# Changelog

## 1.5.0

- `appChannel` changed to `appChannels` (list)
- `appChannel.name` renamed to `appChannels[].channelName`
- `applicationChannelOperator.ingress` moved to `appChannels[].ingress`

## 3.0.0

- Switched to Helm3
- Added `hooks.serviceAccount.name` to specify the serviceAccount used by the post-delete hook `<release>-hook-delete-secrets`
- Added `hooks.serviceAccount.namespace` to specify the serviceAccount namespace (this will also set `<release>-hook-delete-secrets` namespace)

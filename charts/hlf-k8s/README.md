**`appChannel.policy`**

The default Hyperledger Fabric channel policy is `MAJORITY`. This means a node can only be added to the application channel if a majority of the peers already present in the channel agree.

Use this key to set a different application channel policy.

**`appChannel.organizations`**

The organizations to add to the application channel.

The addition of new organizations follows these steps:

1. Create channel update proposal (if none exists)
2. Sign channel update proposal using private key
3. Expose signed channel update proposal on a HTTP endpoint (see `appChannel.fetchProposalOrganizations`)
4. Submit channel update proposal to the orderer

For more info, see the application channel operator in `templates/`

**`appChannel.proposalOrganizations`**

The organizations to fetch application channel update proposals from.

If the application channel is configured using the MAJORITY policy (which is the default), a node can only be added to the application channel if a majority of the peers already present in the channel agree to the addition.

This agreement is achieved though the signature of channel update proposals. The process is as follows:

1. Each peer signs channel update proposals describing the addition of other peers into the channel. Each peer exposes these proposals via a HTTP endpoint (see `appChannel.organizations`)
2. Each peer:
   a) Fetches signed proposals from other peers through the HTTP endpoint.
   b) Then adds their own signature.
   c) Then exposes the updated proposal on their own HTTP endpoint.
3. The process in step 2 continues until enough signatures have been collected.
4. The proposal is submitted to the orderer

For more info, see the application channel operator in `templates/`

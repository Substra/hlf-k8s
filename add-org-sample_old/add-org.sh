
# # Clean Up configuration
echo '----------- CLEAN UP -----------'

rm -f org3.json \
  config.json config.pb \
  modified_config.pb modified_config.json \
  org3_update_in_envelope.pb org3_update_in_envelope.json \
  org3_update.json org3_update.pb  \
  config_block.pb config_block.json

echo '----------- BUILD CONFIG FILE FOR NEW ORG -----------'
configtxgen -printOrg org3 > org3.json
# Add Anchor directly (dirty) with jq
jq '.values.AnchorPeers = {"mod_policy": "Admins", "value": {"anchor_peers": [{"host": "peer1-org3", "port": 7051}]},"version": "0"}' org3.json > org3Anchors.json

mv org3Anchors.json org3.json
# Global variable
export MYCHANNEL='mychannel'
export ORDERER_CA="/data/orgs/orderer/msp/tlscacerts/rca-orderer-7054-rca-orderer.pem"
export CORE_ORDERER_MSPCONFIGPATH='/data/orgs/orderer/msp/'
export CORE_ORDERER_LOCALMSPID="ordererMSP"
export FABRIC_CFG_PATH='/conf/orderer/'

# Fetch with owkin peer
export FABRIC_CFG_PATH='/conf/owkin/peer1/'
export CORE_PEER_MSPCONFIGPATH='/data/orgs/owkin/admin/msp/'
export KEYFILE='/data/orgs/owkin/tls/peer1/client.key'
export CERTFILE='/data/orgs/owkin/tls/peer1/client.crt'


echo '----------- GET CHANNEL CONFIG BLOCK  WITH OWKIN -----------'
peer channel fetch config config_block.pb -o orderer1-orderer:7050 -c ${MYCHANNEL} --tls --clientauth --cafile ${ORDERER_CA} --keyfile ${KEYFILE} --certfile ${CERTFILE}

sleep 2

echo '----------- BUILD CHANNEL UPDATE -----------'
configtxlator proto_decode --input config_block.pb --type common.Block --output config_block.json
cat config_block.json | jq .data.data[0].payload.data.config > config.json

rm config_block.pb config_block.json

jq -s '.[0] * {"channel_group":{"groups":{"Application":{"groups": {"org3":.[1]}}}}}' config.json org3.json > modified_config.json

rm org3.json


configtxlator proto_encode --input config.json --type common.Config --output config.pb
configtxlator proto_encode --input modified_config.json --type common.Config --output modified_config.pb
configtxlator compute_update --channel_id $MYCHANNEL --original config.pb --updated modified_config.pb --output org3_update.pb

configtxlator proto_decode --input org3_update.pb --type common.ConfigUpdate --output org3_update.json


rm config.json config.pb modified_config.json modified_config.pb

echo '{"payload":{"header":{"channel_header":{"channel_id":"mychannel", "type":2}},"data":{"config_update":'$(cat org3_update.json)'}}}' | jq . > org3_update_in_envelope.json


configtxlator proto_encode --input org3_update_in_envelope.json --type common.Envelope --output org3_update_in_envelope.pb


rm org3_update.json org3_update.pb

sleep 2

echo '----------- SIGN UPDATE -----------'
export FABRIC_CFG_PATH='/conf/owkin/peer1/'
export CORE_PEER_MSPCONFIGPATH='/data/orgs/owkin/admin/msp/'
export CORE_PEER_LOCALMSPID="owkinMSP"
export CORE_PEER_TLS_ROOTCERT_FILE='/data/orgs/owkin/admin/msp/cacerts/rca-owkin-7054-rca-owkin.pem'
export CORE_PEER_ADDRESS=peer0-owkin:7053

peer channel signconfigtx -f org3_update_in_envelope.pb -o orderer1-orderer:7050 --tls --clientauth --cafile ${ORDERER_CA} --keyfile ${KEYFILE} --certfile ${CERTFILE}


export CORE_PEER_MSPCONFIGPATH='/data/orgs/chu-nantes/admin/msp/'
export FABRIC_CFG_PATH=/conf/chu-nantes/peer1/
export CORE_PEER_LOCALMSPID="chu-nantesMSP"
export CORE_PEER_TLS_ROOTCERT_FILE='/data/orgs/chu-nantes/admin/msp/cacerts/rca-chu-nantes-7054-rca-chu-nantes.pem'
export CORE_PEER_ADDRESS=peer0-chu-nantes:9053

KEYFILE='/data/orgs/chu-nantes/tls/peer1/client.key'
CERTFILE='/data/orgs/chu-nantes/tls/peer1/client.crt'

sleep 2

echo '----------- PUSH UPDATE -----------'

# peer channel signconfigtx -f org3_update_in_envelope.pb -o orderer1-orderer:7050 --tls --clientauth --cafile ${ORDERER_CA} --keyfile ${KEYFILE} --certfile ${CERTFILE}

peer channel update --logging-level=DEBUG -f org3_update_in_envelope.pb -o orderer1-orderer:7050 -c ${MYCHANNEL} --tls --clientauth --cafile ${ORDERER_CA} --keyfile ${KEYFILE} --certfile ${CERTFILE}
rm -f org3_update_in_envelope.pb org3_update_in_envelope.json

sleep 2

FROM hyperledger/fabric-peer:2.5

COPY ./docker/fabric-peer/core.yaml /etc/hyperledger/fabric/core.yaml
COPY ./docker/fabric-peer/builders /builders

RUN chmod 777 -R /builders

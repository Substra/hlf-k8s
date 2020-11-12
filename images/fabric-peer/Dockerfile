FROM hyperledger/fabric-peer:2.2.1

COPY ./images/fabric-peer/core.yaml /etc/hyperledger/fabric/core.yaml
COPY ./images/fabric-peer/builders /builders

RUN chmod 777 -R /builders

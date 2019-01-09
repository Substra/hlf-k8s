#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
FROM hyperledger/fabric-peer:latest

COPY ./start-peer.py /etc/hyperledger/

# install python 3
RUN apt-get update
RUN apt-get -y install python3

CMD python3 start-peer.py

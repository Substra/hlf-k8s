#
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
FROM hyperledger/fabric-peer:1.4.1

RUN apt-get update
RUN apt-get install -y curl netcat

COPY ./bootstrap-binaries.sh /tmp
RUN cd /tmp; sh bootstrap-binaries.sh;

RUN cp /tmp/bin/fabric-ca-client /usr/local/bin/
RUN chmod +x /usr/local/bin/fabric-ca-client

COPY ./start-peer.py /etc/hyperledger/

# install python 3
RUN apt-get -y install python3

CMD python3 start-peer.py

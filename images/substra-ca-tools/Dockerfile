#
# Copyright substra. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

FROM hyperledger/fabric-tools:1.4.1-rc1

RUN apt-get update
RUN apt-get install -y curl netcat

COPY ./bootstrap-binaries.sh /tmp
RUN cd /tmp; sh bootstrap-binaries.sh;

RUN cp /tmp/bin/fabric-ca-client /usr/local/bin/
RUN chmod +x /usr/local/bin/fabric-ca-client

RUN apt-get install -y libssl-dev python3-dev python3-setuptools python3-pip libffi-dev
COPY requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

# install fabric-sdk-py and make hfc package available globally
RUN git clone https://github.com/hyperledger/fabric-sdk-py.git && cd fabric-sdk-py && make install
ENV PYTHONPATH=$PYTHONPATH:/fabric-sdk-py

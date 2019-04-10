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

RUN apt-get install -y python3-dev python3-setuptools python3-pip
RUN pip3 install --upgrade pip
COPY requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt


#
# Copyright substra. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
FROM hyperledger/fabric-tools:1.4.6

RUN echo "deb http://cn.archive.ubuntu.com/ubuntu bionic main multiverse restricted universe" >> /etc/apt/sources.list
RUN echo "deb http://cn.archive.ubuntu.com/ubuntu bionic-updates main multiverse restricted universe" >> /etc/apt/sources.list
RUN echo "deb http://cn.archive.ubuntu.com/ubuntu bionic-security main multiverse restricted universe" >> /etc/apt/sources.list
RUN echo "deb http://cn.archive.ubuntu.com/ubuntu bionic-proposed main multiverse restricted universe" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y curl netcat python3-pip python3.6-dev libssl-dev python3-setuptools python3-pip libffi-dev docker.io

COPY images/substra-ca-tools-debug/bootstrap-binaries.sh /tmp
RUN cd /tmp; sh bootstrap-binaries.sh;

RUN cp /tmp/bin/fabric-ca-client /usr/local/bin/
RUN chmod +x /usr/local/bin/fabric-ca-client

COPY images/substra-ca-tools-debug/requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /scripts/
COPY ./python-scripts /scripts/

#
# Copyright substra. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
FROM hyperledger/fabric-ca-tools:latest

RUN apt-get update
RUN apt-get install -y python3-dev python3-setuptools python3-pip
RUN pip3 install --upgrade pip
COPY requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt


# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from .peers.peer1 import peer1
from .peers.peer2 import peer2
from .users.admin import admin
from .users.bootstrap_admin import bootstrap_admin
from .users.user import user


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

clb = {
    'type': 'client',
    'name': 'clb',
    'mspid': 'clbMSP',
    'anchor_tx_file': f'{SUBSTRA_PATH}/data/orgs/clb/anchors.tx',
    'tls': {
        # careful, `ca-cert.pem` is the default cert name file and a example file with this name is already present in
        # the docker image, do not forget to remove these examples files in your docker CMD overriding if naming the same way
        'certfile': {
            'external': f'{SUBSTRA_PATH}/data/orgs/clb/tls-ca-cert.pem',
            'internal': '/etc/hyperledger/fabric/ca/tls-ca-cert.pem'
        },
        'clientkey': ''
    },
    'ca': {
        'name': 'rca-clb',
        'host': 'rca-clb',
        'certfile': {
            'external': f'{SUBSTRA_PATH}/data/orgs/clb/ca-cert.pem',
            'internal': '/etc/hyperledger/fabric/ca/ca-cert.pem'
        },
        'keyfile': {
            'external': f'{SUBSTRA_PATH}/data/orgs/clb/ca-key.pem',
            'internal': '/etc/hyperledger/fabric/ca/ca-key.pem'
        },
        'port': {
            'internal': 7054,
            'external': 10054
        },
        'url': 'https://rca-clb:7054',
        'logfile': f'{SUBSTRA_PATH}/data/log/rca-clb.log',
        'server-config-path': f'{SUBSTRA_PATH}/conf/clb/fabric-ca-server-config.yaml',
        'client-config-path': f'{SUBSTRA_PATH}/conf/clb/fabric-ca-client-config.yaml',
        'affiliations': {
            'clb': ['lyon']
        },
        'users': {
            'bootstrap_admin': bootstrap_admin,
        },
    },
    'users': {
        'admin': admin,
        'user': user,
    },
    'csr': {
        'cn': 'rca-clb',
        # The "hosts" value is a list of the domain names which the certificate should be valid for.
        'hosts': ['rca-clb'],
        'names': [
            {'C': 'FR',
             'ST': 'Rhone',
             'L': 'Lyon',
             'O': 'clb',
             'OU': None}
        ],
    },
    'core_dir': {
        'internal': '/etc/hyperledger/fabric',
    },
    'peers': [peer1, peer2]
}

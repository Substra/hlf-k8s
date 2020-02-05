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


SUBSTRA_PATH = os.getenv('SUBSTRA_PATH', '/substra')

peer2 = {
    'name': 'peer2-chu-nantes',
    'pass': 'peer2pw',
    'host': 'peer2-chu-nantes',
    'port': {
        'internal': 7051,
        'external': 10051
    },
    'operations': {
        'prometheus': {
            'port': {
                'internal': 9443,
                'external': 13443
            }
        },
        'statsd': {
            'port': {
                'internal': 8125,
                'external': 11125
            }
        },
    },
    'anchor': False,
    'tls': {
        'dir': {
            'external': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/tls/peer2',
            'internal': '/etc/hyperledger/fabric/tls'
        },
        'client': {
            'dir': 'client',
            'cert': 'client.crt',
            'key': 'client.key',
            'ca': 'client.pem'
        },
        'server': {
            'dir': 'server',
            'cert': 'server.crt',
            'key': 'server.key',
            #  paradoxically, this will not be a tls certificate,
            #  but will be put by fabric-ca inside tlscacerts directory
            # it will be equal to org['ca']['certfile']
            'ca': 'server.pem'
        },
    }
}

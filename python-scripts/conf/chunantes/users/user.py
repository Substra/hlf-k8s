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

user = {
    'name': 'user-chu-nantes',
    'pass': 'user-chu-nantespw',
    'home': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/user',
    'cert': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/user/msp/signcerts/cert.pem',
    'private_key': f'{SUBSTRA_PATH}/data/orgs/chu-nantes/user/msp/keystore/key.pem',
}

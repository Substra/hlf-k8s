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

import json
import time
import sys

import substra


USER, PASSWORD = ('substra', 'p@$swr0d44')
client = substra.Client()
client.add_profile('owkin', USER, PASSWORD, 'http://substra-backend.owkin.xyz:8000')
client.login()


def load_tuple_keys(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return (data['traintupleKeys'], data['testtupleKeys'])


def watch_tuples(traintuple_keys, testtuple_keys):
    # watch all tuples until they are in done/failed state
    print(f'Watching traintuple keys: {traintuple_keys}')
    print(f'Watching testtuple keys: {testtuple_keys}')

    failed = False

    conf = (
        ('traintuple', traintuple_keys, client.list_traintuple),
        ('testtuple', testtuple_keys, client.list_testtuple)
    )

    while traintuple_keys and testtuple_keys:
        for tuple_type, tuple_keys, list_tuple in conf:
            tuple_filter = [f'{tuple_type}:key:{key}' for key in tuple_keys]
            tuples = list_tuple(filters=tuple_filter)

            for tuple_ in tuples:
                if tuple_['status'] == 'failed':
                    print(f'{tuple_type} failed: {tuple_["key"]}')
                    failed = True
                if tuple_['status'] in ('done', 'failed'):
                    print(f'{tuple_type} done: {tuple_["key"]}')
                    tuple_keys.remove(tuple_['key'])

        time.sleep(2)

    if failed:
        raise ValueError("At least one of the tuples failed")

    print(f'All traintuples and testtuples reached the "done" status')


if __name__ == '__main__':
    path = sys.argv.pop()
    traintuple_keys, testtuple_keys = load_tuple_keys(path)
    watch_tuples(traintuple_keys, testtuple_keys)

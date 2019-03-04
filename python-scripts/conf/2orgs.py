import json

from misc import misc
from orderer import orderer
from owkin import owkin
from chunantes import chunantes

misc.update({
    'fixtures_path': 'fixtures2orgs.py'
})

conf = {
    'orgs': [owkin, chunantes],
    'orderers': [orderer],
    'misc': misc,
}

if __name__ == '__main__':
    with open('/substra/conf/conf.json', 'w+') as write_file:
        json.dump(conf, write_file, indent=True)

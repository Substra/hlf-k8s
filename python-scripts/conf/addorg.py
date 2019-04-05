import json

from misc import misc
from orderer import orderer
from chunantes import chunantes

conf = {
    'orgs': [chunantes],
    'orderers': [orderer],
    'misc': misc,
}

if __name__ == '__main__':
    with open('/substra/conf/conf-add.json', 'w+') as write_file:
        json.dump(conf, write_file, indent=True)

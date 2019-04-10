import json
import os
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call

from setup import registerPeerIdentities, registerUsers


if __name__ == '__main__':

    conf_path = '/substra/conf/conf-org.json'
    conf = json.load(open(conf_path, 'r'))

    conf['orderers'] = []  # Hack for setup
    registerPeerIdentities(conf)
    registerUsers(conf)

    print('Finished setup', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

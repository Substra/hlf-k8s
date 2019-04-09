import json
import os
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call

from setup import registerPeerIdentities, registerUsers, generateChannelArtifacts


if __name__ == '__main__':

    conf_path = '/substra/conf/conf-org.json'
    conf = json.load(open(conf_path, 'r'))

    conf['orderers'] = []  # Hack for setup
    registerPeerIdentities(conf)
    registerUsers(conf)

    conf_path = '/substra/conf/conf-org.json'
    conf = json.load(open(conf_path, 'r'))

    if not os.path.exists(conf['misc']['channel_tx_file']):
        generateChannelArtifacts(conf)

    print('Finished building channel artifacts', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

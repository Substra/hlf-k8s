import json
# from hfc.fabric_ca.caservice import ca_service
from subprocess import call

from setup import registerOrdererIdentities, registerUsers, generateGenesis


if __name__ == '__main__':

    conf_path = '/substra/conf/conf.json'
    conf = json.load(open(conf_path, 'r'))

    registerOrdererIdentities(conf)
    conf['orgs'] = []  # Hack for setup
    registerUsers(conf)
    generateGenesis(conf)
    print('Finished building channel artifacts', flush=True)
    call(['touch', conf['misc']['setup_success_file']])

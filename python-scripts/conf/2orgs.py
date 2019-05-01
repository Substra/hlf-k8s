import json

from misc import misc
from orderer import orderer
from owkin import owkin
from chunantes import chunantes

misc.update({
    'fixtures_path': 'fixtures2orgs.py'
})


def main():

    conf = {
        'service': orderer,
        'misc': {k: misc[k] for k in ['system_channel_name', 'channel_name', 'channel_block', 'chaincode_name',
                                      'chaincode_version', 'genesis_bloc_file', 'channel_tx_file',
                                      'configtx-config-path', 'config_block_file', 'config_update_envelope_file',
                                      'setup_logfile', 'setup_success_file', ]},
    }

    service_name = orderer['name']
    conf['misc']['setup_logfile'] = f'/substra/data/log/setup-{service_name}.log',
    conf['misc']['configtx-config-path'] = f'/substra/data/configtx-{service_name}.yaml'
    conf['misc']['setup_success_file'] = f'/substra/data/log/setup-{service_name}.successful'

    with open('/substra/conf/config/conf-orderer.json', 'w+') as write_file:
        json.dump(conf, write_file, indent=4)

    for org in [owkin, chunantes]:
        conf = {
            'service': org,
            'misc': dict(misc),
        }

        service_name = org['name']
        conf['misc']['configtx-config-path'] = f'/substra/data/configtx-{service_name}.yaml'
        conf['misc']['setup_logfile'] = f'/substra/data/log/setup-{service_name}.log',
        conf['misc']['setup_success_file'] = f'/substra/data/log/setup-{service_name}.successful'
        conf['misc']['run_logfile'] = f'/substra/data/log/run-{service_name}.log'
        conf['misc']['run_sumfile'] = f'/substra/data/log/run-{service_name}.sum'
        conf['misc']['run_success_file'] = f'/substra/data/log/run-{service_name}.successful'
        conf['misc']['run_fail_file'] = f'/substra/data/log/run-{service_name}.fail'

        with open(f'/substra/conf/config/conf-{service_name}.json', 'w+') as write_file:
            json.dump(conf, write_file, indent=4)


if __name__ == '__main__':
    main()

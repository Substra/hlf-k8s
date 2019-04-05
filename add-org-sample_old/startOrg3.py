import os

from subprocess import call, check_output
from confOrg3 import conf
from util import dowait, create_directory, remove_chaincode_docker_images, remove_chaincode_docker_containers

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

dir_path = os.path.dirname(os.path.realpath(__file__))


def create_ca_server_config(orgs):
    # For each org, create a config file from template
    for org_name in orgs.keys():
        org = orgs[org_name]

        stream = open(os.path.join(dir_path, '../templates/fabric-ca-server-config.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['tls']['certfile'] = org['tls']['certfile']

        yaml_data['ca']['name'] = org['ca']['name']
        yaml_data['ca']['certfile'] = org['ca']['certfile']

        yaml_data['csr']['cn'] = org['csr']['cn']
        yaml_data['csr']['hosts'] += org['csr']['hosts']

        yaml_data['registry']['identities'][0]['name'] = org['users']['bootstrap_admin']['name']
        yaml_data['registry']['identities'][0]['pass'] = org['users']['bootstrap_admin']['pass']

        filename = os.path.join(dir_path, '../conf/%(org)s/fabric-ca-server-config.yaml' % {'org': org_name})
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_ca_client_config(orgs):
    # For each org, create a config file from template
    for org_name in orgs.keys():
        org = orgs[org_name]

        stream = open(os.path.join(dir_path, '../templates/fabric-ca-client-config.yaml'), 'r')
        yaml_data = load(stream, Loader=Loader)

        # override template here
        yaml_data['tls']['certfiles'] = org['tls']['certfile']

        yaml_data['caname'] = org['ca']['name']

        yaml_data['csr']['cn'] = org['csr']['cn']
        yaml_data['csr']['hosts'] += org['csr']['hosts']

        yaml_data['url'] = org['ca']['url']

        filename = os.path.join(dir_path, '../conf/%(org)s/fabric-ca-client-config.yaml' % {'org': org_name})
        with open(filename, 'w+') as f:
            f.write(dump(yaml_data, default_flow_style=False))


def create_ca():
    print('Creating ca server/client files for each orgs', flush=True)
    create_ca_server_config(conf['orgs'])
    create_ca_client_config(conf['orgs'])


def create_core_peer_config():
    for org_name in conf['orgs'].keys():
        org = conf['orgs'][org_name]
        for peer in org['peers']:
            stream = open(os.path.join(dir_path, '../templates/core.yaml'), 'r')
            yaml_data = load(stream, Loader=Loader)

            # override template here

            yaml_data['peer']['id'] = peer['host']
            yaml_data['peer']['address'] = '%(host)s:%(port)s' % {'host': peer['host'], 'port': peer['port']}
            yaml_data['peer']['localMspId'] = org['org_msp_id']
            yaml_data['peer']['mspConfigPath'] = org['core']['msp_config_path']

            yaml_data['peer']['tls']['cert']['file'] = org['core']['peer_home'] + '/tls/' + org['core']['tls']['cert']
            yaml_data['peer']['tls']['key']['file'] = org['core']['peer_home'] + '/tls/' + org['core']['tls']['key']
            yaml_data['peer']['tls']['clientCert']['file'] = '/data/orgs/' + org_name + '/tls/' + peer[
                'name'] + '/cli-client.crt'
            yaml_data['peer']['tls']['clientKey']['file'] = '/data/orgs/' + org_name + '/tls/' + peer[
                'name'] + '/cli-client.key'
            yaml_data['peer']['tls']['enabled'] = 'true'
            yaml_data['peer']['tls']['rootcert']['file'] = org['tls']['certfile']
            yaml_data['peer']['tls']['clientAuthRequired'] = 'true'
            yaml_data['peer']['tls']['clientRootCAs'] = [org['tls']['certfile']]

            yaml_data['peer']['gossip']['useLeaderElection'] = 'true'
            yaml_data['peer']['gossip']['orgLeader'] = 'false'
            yaml_data['peer']['gossip']['externalEndpoint'] = peer['host'] + ':' + str(peer['port'])
            yaml_data['peer']['gossip']['skipHandshake'] = 'true'

            yaml_data['vm']['endpoint'] = 'unix:///host/var/run/docker.sock'
            yaml_data['vm']['docker']['hostConfig']['NetworkMode'] = 'net_substra'

            yaml_data['logging']['level'] = 'debug'

            create_directory(os.path.join(dir_path, '../conf/%(org_name)s/%(peer_name)s' % {'org_name': org_name, 'peer_name': peer['name']}))
            filename = os.path.join(dir_path, '../conf/%(org_name)s/%(peer_name)s/core.yaml' % {'org_name': org_name,
                                                                                                'peer_name': peer['name']})
            with open(filename, 'w+') as f:
                f.write(dump(yaml_data, default_flow_style=False))


def stop():
    print('stopping container', flush=True)
    call(['docker-compose', '-f', os.path.join(dir_path, '../docker-composeOrg3.yaml'), 'down'])


def start():
    create_ca()
    create_core_peer_config()

    stop()

    print('start docker-compose', flush=True)
    call(['docker-compose', '-f', os.path.join(dir_path, '../docker-composeOrg3.yaml'), 'up', '-d',
          'rca-org3', 'setupOrg3', 'peer1-org3', 'peer2-org3'])
    call(['docker', 'ps', '-a'])

    # Wait for the setup container to complete
    dowait('the \'setup\' container to finish registering identities, creating the genesis block and other artifacts',
           90, os.path.join(dir_path, '..' + conf['misc']['setup_logfile']),
           [os.path.join(dir_path, '..' + conf['misc']['setup_success_file'])])

    call(['docker-compose', '-f', os.path.join(dir_path, '../docker-composeOrg3.yaml'), 'up', '--no-deps', '-d', 'runOrg3'])
    dowait('the docker \'run\' container to run and complete',
           160, os.path.join(dir_path, '..' + conf['misc']['run_logfile']),
           [os.path.join(dir_path, '..' + conf['misc']['run_success_file'])])


if __name__ == "__main__":
    # create directory with correct rights
    # careful you need to be sudo for this to work
    call(['rm', '-rf', os.path.join(dir_path, '../data/org/org3')])
    call(['rm', '-rf', os.path.join(dir_path, '../conf/org3')])
    call(['rm', '-rf', os.path.join(dir_path, '../data/logs/setupOrg3.successful')])

    # create_directory(os.path.join(dir_path, '../data/logs'))
    for org in list(conf['orgs'].keys()):
        create_directory(os.path.join(dir_path, '../data/orgs/%s' % org))
        create_directory(os.path.join(dir_path, '../conf/%s' % org))

    start()

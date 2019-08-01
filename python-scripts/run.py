import glob
import os
import json
import time
from subprocess import call

from hfc.fabric_ca.caservice import ca_service

from utils.cli import init_cli, update_cli
from utils.run_utils import Client, ChannelAlreadyExist
from utils.common_utils import remove_chaincode_docker_containers


# We need to retry as we cannot know when the channel is created and its genesis block is available
# Unfortunately, there is currently no other way to know when a channel has been created
def waitForPeersToJoinchannel():
    timeout = 30
    start = 0

    print('Wait For Peers to join channel', flush=True)
    print(f"Join channel {client.channel_name} with peers {[x.name for x in client.org_peers]} ...", flush=True)

    while start < timeout:
        # make peers join channel
        try:
            client.peersJoinChannel()
        except Exception as e:
            print(e)
            print('Will retry to make peers join channel', flush=True)
            start += 1
            time.sleep(1)
        else:
            print(f'Peers {[x.name for x in client.org_peers]} successfully joined channel {client.channel_name}')
            break


def add_org():
    # make current org in consortium of system channel for being able to create channel
    config_tx_file = client.createSystemUpdateProposal()
    client.signAndPushSystemUpdateProposal(config_tx_file)

    # generate channel configuration from configtx.yaml
    client.generateChannelArtifacts()

    try: # create channel
        client.createChannel()
    except ChannelAlreadyExist:  # add new org in channel, upgrade chaincode
        # make new org know channel already created
        client.cli.new_channel(client.channel_name)

        ####
        # load external confs of orgs already in consortium
        ####

        # get channel config on application channel
        old_channel_config_envelope = client.getChannelConfigBlockWithOrderer(client.channel_name)
        external_orgs = old_channel_config_envelope['config']['channel_group']['groups']['Application']['groups'].keys()
        print('external_orgs: ', list(external_orgs))

        # get conf files
        files = glob.glob(f'{substra_path}/conf/config/conf-*.json')
        files = [file_path for file_path in files
                 if file_path.split(f'{substra_path}/conf/config/conf-')[-1].split('.json')[0] in external_orgs]
        conf_externals = [json.load(open(file_path, 'r')) for file_path in files]
        # add conf_externals in cli
        update_cli(client.cli, conf_externals)

        # update channel for making it know new org
        client.generateChannelUpdate(conf, conf_externals, old_channel_config_envelope['config'])

        # make peers join channel
        waitForPeersToJoinchannel()

        # update chaincode version, as new org
        chaincode_version = client.getChaincodeVersion(conf_externals[0])
        new_chaincode_version = '%.1f' % (chaincode_version + 1.0)

        # Install chaincode on peer in each org
        orgs_mspid = []
        for conf_org in [conf] + conf_externals:
            client.installChainCodeOnPeers(conf_org, new_chaincode_version)
            orgs_mspid.append(conf_org['mspid'])

        # upgrade chaincode with new policy
        client.upgradeChainCode(conf_externals[0], orgs_mspid, new_chaincode_version, 'init')

        # TODO deplace in substrabac with a discovery
        # for each external node, make them create an account for us to authent to them
        for conf_org in conf_externals:
            target = f"https://{conf_org['ca']['host']}:{conf_org['ca']['port']['internal']}"
            cacli = ca_service(target=target,
                               ca_certs_path=conf_org['ca']['certfile']['external'],  # TODO, make it available internal
                               ca_name=conf_org['ca']['name'])
            bootstrap_admin = cacli.enroll(conf_org['ca']['users']['bootstrap_admin']['name'],
                                           conf_org['ca']['users']['bootstrap_admin']['pass'])
            print(f"Will register {conf['external']['user']['name']} with {conf['external']['user']['pass']} on {target}", flush=True)
            secret = bootstrap_admin.register(conf['external']['user']['name'], conf['external']['user']['pass'], maxEnrollments=-1)
            print(secret, flush=True)

            # make this username/pass available in a file for substrabac to load it and can compute cert for its mapping
            external_path = conf_org['external']['path']
            permission_name = conf['name'].replace('-', '')
            try:
                with open(external_path, 'r+') as f:
                    data = json.load(f)
            except:
                data = {permission_name: {}}

            if permission_name not in data:
                data = {permission_name: {}}

            data[permission_name].update({
                conf['external']['user']['name']: conf['external']['user']['pass']
            })
            os.makedirs(os.path.dirname(external_path), exist_ok=True)
            with open(external_path, 'w+') as f:
                json.dump(data, f)

        # create an account for all users of external orgs for them to authent to us too
        target = f"https://{conf['ca']['host']}:{conf['ca']['port']['internal']}"
        cacli = ca_service(target=target,
                           ca_certs_path=conf['ca']['certfile']['external'],  # TODO, make it available internal
                           ca_name=conf['ca']['name'])
        bootstrap_admin = cacli.enroll(conf['ca']['users']['bootstrap_admin']['name'],
                                       conf['ca']['users']['bootstrap_admin']['pass'])
        for conf_org in conf_externals:
            print(
                f"Will register {conf_org['external']['user']['name']} with {conf_org['external']['user']['pass']} on {target}",
                flush=True)
            secret = bootstrap_admin.register(conf_org['external']['user']['name'], conf_org['external']['user']['pass'],
                                     maxEnrollments=-1)
            print(secret, flush=True)

            # make this username/pass available in a file for substrabac to load it and can compute cert for its mapping
            external_path = conf['external']['path']
            permission_name = conf_org['name'].replace('-', '')
            try:
                with open(external_path, 'r+') as f:
                    data = json.load(f)
            except:
                data = {permission_name: {}}

            if permission_name not in data:
                data = {permission_name: {}}

            data[permission_name].update({
                conf_org['external']['user']['name']: conf_org['external']['user']['pass']
            })
            os.makedirs(os.path.dirname(external_path), exist_ok=True)
            with open(external_path, 'w+') as f:
                json.dump(data, f)

        remove_chaincode_docker_containers(chaincode_version)

    else:  # channel is created, install + instantiate chaincode

        # make peers join channel
        waitForPeersToJoinchannel()

        # update anchor peers if needed (normally already present in configtx.yaml)
        #client.updateAnchorPeers()

        # Install chaincode on peer in each org
        client.installChainCodeOnPeers(conf, conf['misc']['chaincode_version'])

        # Instantiate chaincode on peers (could be done on only one peer)
        client.instanciateChaincode()

    # Query chaincode
    if client.queryChaincodeFromPeers() == '[]':
        print('Congratulations! Ledger has been correctly initialized.', flush=True)
        call(['touch', conf['misc']['run_success_file']])
    else:
        print('Fail to initialize ledger.', flush=True)
        call(['touch', conf['misc']['run_fail_file']])


if __name__ == "__main__":
    org_name = os.environ.get('ORG')
    substra_path = os.environ.get('SUBSTRA_PATH')

    print(os.path.join(substra_path, 'conf/config', f'conf-{org_name}.json'))

    conf = json.load(open(os.path.join(substra_path, 'conf/config', f'conf-{org_name}.json'), 'r'))
    conf_orderer = json.load(open(os.path.join(substra_path, 'conf/config', f'conf-orderer.json'), 'r'))

    cli = init_cli([conf, conf_orderer])
    client = Client(cli, conf, conf_orderer)
    add_org()

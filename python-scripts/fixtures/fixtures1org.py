import json
import os
import time
import subprocess

from conf2orgs import conf
from subprocess import call, check_output, CalledProcessError


def set_env_variables(fabric_cfg_path, msp_dir):
    os.environ['FABRIC_CFG_PATH'] = fabric_cfg_path
    os.environ['CORE_PEER_MSPCONFIGPATH'] = msp_dir


def clean_env_variables():
    del os.environ['FABRIC_CFG_PATH']
    del os.environ['CORE_PEER_MSPCONFIGPATH']


def chainCodeQueryWith(arg, org, peer):
    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_user_msp_dir)

    channel_name = conf['misc']['channel_name']
    chaincode_name = conf['misc']['chaincode_name']

    print('Querying chaincode in the channel \'%(channel_name)s\' on the peer \'%(peer_host)s\' ...' % {
        'channel_name': channel_name,
        'peer_host': peer['host']
    }, flush=True)

    try:
        output = check_output(['peer', 'chaincode', 'query',
                               '-C', channel_name,
                               '-n', chaincode_name,
                               '-c', arg]).decode()
    except CalledProcessError as e:
        output = e.output.decode()
        print('Error:', flush=True)
        print(output, flush=True)
        # clean env variables
        clean_env_variables()
    else:
        try:
            value = json.loads(output)
        except:
            value = output
        else:
            msg = 'Query of channel \'%(channel_name)s\' on peer \'%(peer_host)s\' was successful' % {
                'channel_name': channel_name,
                'peer_host': peer['host']
            }
            print(msg, flush=True)
            print(value, flush=True)

        finally:
            # clean env variables
            clean_env_variables()
            return value


def queryChaincodeFromFirstPeerFirstOrgAfterInvoke():
    org_name = 'owkin'
    org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    peer = org['peers'][0]

    print('Try to query chaincode from first peer first org after invoke', flush=True)

    starttime = int(time.time())
    while int(time.time()) - starttime < 15:
        call(['sleep', '1'])
        data = chainCodeQueryWith('{"Args":["queryChallenges"]}',
                                  org,
                                  peer)
        # data should not be null
        print(data, flush=True)
        if isinstance(data, list) and len(data) == 2:
            print('Correctly added and got', flush=True)
            return True

        print('.', end='', flush=True)

    print('\n/!\ Failed to query chaincode after invoke', flush=True)
    return False


def invokeChainCode(args, org, peer):
    org_user_home = org['users']['user']['home']
    org_user_msp_dir = org_user_home + '/msp'
    orderer = conf['orderers'][0]
    channel_name = conf['misc']['channel_name']
    chaincode_name = conf['misc']['chaincode_name']

    # update config path for using right core.yaml and right msp dir
    set_env_variables(peer['docker_core_dir'], org_user_msp_dir)

    print('Sending invoke transaction (with waitForEvent) to %(PEER_HOST)s ...' % {'PEER_HOST': peer['host']},
          flush=True)

    output = subprocess.run(['peer',
                             'chaincode', 'invoke',
                             '-C', channel_name,
                             '-n', chaincode_name,
                             '-c', args,
                             '-o', '%(host)s:%(port)s' % {'host': orderer['host'], 'port': orderer['port']},
                             '--tls',
                             '--clientauth',
                             '--cafile', orderer['ca']['certfile'],
                             '--keyfile', peer['tls']['clientKey'],
                             '--certfile', peer['tls']['clientCert'],
                             '--waitForEvent'
                             ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    data = output.stderr.decode('utf-8')

    print(data, flush=True)

    # clean env variables
    clean_env_variables()

    try:
        # Format it to get generated key
        data = data.split('result: status:')[1].split('\n')[0].split('payload:')[1].replace(' ', '').replace('"', '')
    except:
        return ''
    else:
        return data


def invokeChaincodeFirstPeers():
    org_name = 'owkin'
    org = [x for x in conf['orgs'] if x['name'] == org_name][0]
    peer = org['peers'][0]

    # should fail
    args = '{"Args":["registerDataset","liver slide"]}'
    invokeChainCode(args, org, peer)

    # create dataset with owkin org
    args = '{"Args":["registerDataset","ISIC 2018","ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994","http://owkin.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/opener/","Images","7a90514f88c70002608a9868681dd1589ea598e78d00a8cd7783c3ea0f9ceb09","http://owkin.substrabac:8001/dataset/ccbaa3372bc74bce39ce3b138f558b3a7558958ef2f244576e18ed75b0cea994/description/","","all"]}'
    dataset_owkin = invokeChainCode(args, org, peer)

    # register train data on dataset owkin (will take dataset creator as worker)
    args = '{"Args":["registerData","62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9","%s","false"]}' % dataset_owkin
    invokeChainCode(args, org, peer)

    # create dataset, test data and challenge on owkin

    # create second dataset with owkin org
    args = '{"Args":["registerDataset","Simplified ISIC 2018","b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0","http://owkin.substrabac:8000/dataset/b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0/opener/","Images","258bef187a166b3fef5cb86e68c8f7e154c283a148cd5bc344fec7e698821ad3","http://owkin.substrabac:8000/dataset/b4d2deeb9a59944d608e612abc8595c49186fa24075c4eb6f5e6050e4f9affa0/description/","","all"]}'
    dataset_owkin2 = invokeChainCode(args, org, peer)

    # register test data on dataset on owkin center (will take dataset creator as worker)
    args = '{"Args":["registerData","e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1, 4b5152871b181d10ee774c10458c064c70710f4ba35938f10c0b7aa51f7dc010", "%s","true"]}' % dataset_owkin
    invokeChainCode(args, org, peer)

    # register train data on dataset_owkin
    args = '{"Args":["registerData","93e4b1e040b08cfa8a68b13f9dddb95a6672e8a377378545b2b1254691cfc060, eed4c6ea09babe7ca6428377fff6e54102ef5cdb0cae593732ddbe3f224217cb", "%s","true"]}' % dataset_owkin
    invokeChainCode(args, org, peer)

    # register test data on dataset_owkin
    args = '{"Args":["registerData","2d0f943aa81a9cb3fe84b162559ce6aff068ccb04e0cb284733b8f9d7e06517e, 533ee6e7b9d8b247e7e853b24547f57e6ef351852bac0418f13a0666173448f1", "%s","true"]}' % dataset_owkin
    invokeChainCode(args, org, peer)

    args = '{"Args":["queryDatasets"]}'
    chainCodeQueryWith(args, org, peer)

    # create challenge
    args = '{"Args":["registerChallenge", "Simplified skin lesion classification", "6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c", "http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/description/", "macro-average recall", "0bc732c26bafdc41321c2bffd35b6835aa35f7371a4eb02994642c2c3a688f60", "http://owkin.substrabac:8000/challenge/6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c/metrics/", "%s:2d0f943aa81a9cb3fe84b162559ce6aff068ccb04e0cb284733b8f9d7e06517e, 533ee6e7b9d8b247e7e853b24547f57e6ef351852bac0418f13a0666173448f1", "all"]}' % dataset_owkin
    invokeChainCode(args, org, peer)

    # create challenge
    args = '{"Args":["registerChallenge", "Skin Lesion Classification Challenge", "d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f", "http://owkin.substrabac:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/description/", "macro-average recall", "750f622262854341bd44f55c1018949e9c119606ef5068bd7d137040a482a756", "http://owkin.substrabac:8001/challenge/d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f/metrics/", "%s:e11aeec290749e4c50c91305e10463eced8dbf3808971ec0c6ea0e36cb7ab3e1", "all"]}' % dataset_owkin2
    invokeChainCode(args, org, peer)

    # create algo
    args = '{"Args":["registerAlgo","Logistic regression","9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a","http://owkin.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/file/","124a0425b746d7072282d167b53cb6aab3a31bf1946dae89135c15b0126ebec3","http://owkin.substrabac:8001/algo/9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a/description/","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    invokeChainCode(args, org, peer)

    # create second algo on challenge Simplified skin lesion classification
    args = '{"Args":["registerAlgo","Logistic regression for balanced problem","7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0","http://owkin.substrabac:8001/algo/7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0/file/","3b1281cbdd6ebfec650d0a9f932a64e45a27262848065d7cecf11fd7191b4b1f","http://owkin.substrabac:8001/algo/7742aea2001ceb40e9ce8a37fa27237d5b2d1f574e06d48677af945cfdf42ec0/description/","6b8d16ac3eae240743428591943fa8e66b34d4a7e0f4eb8e560485c7617c222c","all"]}'
    invokeChainCode(args, org, peer)

    # create third algo
    args = '{"Args":["registerAlgo","Neural Network","0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f","http://owkin.substrabac:8001/algo/0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f/file/","b9463411a01ea00869bdffce6e59a5c100a4e635c0a9386266cad3c77eb28e9e","http://owkin.substrabac:8001/algo/0acc5180e09b6a6ac250f4e3c172e2893f617aa1c22ef1f379019d20fe44142f/description/","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    invokeChainCode(args, org, peer)

    # create fourth algo
    args = '{"Args":["registerAlgo","Random Forest","f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284","http://owkin.substrabac:8001/algo/f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284/file/","4acea40c4b51996c88ef279c5c9aa41ab77b97d38c5ca167e978a98b2e402675","http://owkin.substrabac:8001/algo/f2d9fd38e25cd975c49f3ce7e6739846585e89635a86689b5db42ab2c0c57284/description/","d5002e1cd50bd5de5341df8a7b7d11b6437154b3b08f531c9b8f93889855c66f","all"]}'
    invokeChainCode(args, org, peer)

    # query data of the dataset in owkin
    args = '{"Args":["queryDatasetData","%s"]}' % dataset_owkin
    chainCodeQueryWith(args, org, peer)

    args = '{"Args":["queryTraintuples"]}'
    chainCodeQueryWith(args, org, peer)

    args = '{"Args":["createTraintuple","9ca7ffbdbb55156b0fb44a227c3c305b7f7300113b6008c662460cf0f8f7cc3a","","%s","62fb3263208d62c7235a046ee1d80e25512fe782254b730a9e566276b8c0ef3a, 42303efa663015e729159833a12ffb510ff92a6e386b8152f90f6fb14ddc94c9", "", ""]}' % dataset_owkin
    traintuple = invokeChainCode(args, org, peer)

    # recreation of traintuple should fail
    invokeChainCode(args, org, peer)

    args = '{"Args":["logStartTrain","' + traintuple + '"]}'
    invokeChainCode(args, org, peer)

    args = '{"Args":["queryTraintuples"]}'
    chainCodeQueryWith(args, org, peer)

    args = '{"Args":["logSuccessTrain","' + traintuple + '","10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568, http://owkin.substrabac:8001/model/10060f1d9e450d98bb5892190860eee8dd48594f00e0e1c9374a27c5acdba568/file/","0.91","no error, ah ah ah"]}'
    invokeChainCode(args, org, peer)

    args = '{"Args":["createTesttuple","%s"]}' % traintuple
    testtuple = invokeChainCode(args, org, peer)

    args = '{"Args":["logStartTest","' + testtuple + '"]}'
    invokeChainCode(args, org, peer)

    args = '{"Args":["logSuccessTest","' + testtuple + '","0.99","still no error, suprah ah ah"]}'
    invokeChainCode(args, org, peer)


def run():
    res = True

    # Invoke chaincode with 1st peers of each org
    invokeChaincodeFirstPeers()

    # Query chaincode from the 1st peer of the 1st org after Invoke
    res = res and queryChaincodeFromFirstPeerFirstOrgAfterInvoke()

    if res:
        print('Congratulations! The fixtures have been loaded successfully.', flush=True)
        call(['touch', conf['misc']['fixtures_success_file']])
    else:
        print('Loading fixtures failed.', flush=True)
        call(['touch', conf['misc']['fixtures_fail_file']])


if __name__ == "__main__":
    run()

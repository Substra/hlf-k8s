import os
from shutil import copytree
from subprocess import call

from hfc.fabric_ca.caservice import ca_service
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes


from .common_utils import waitPort, dowait


def removeIntermediateCerts(intermediatecerts_dir):
    print(f'Delete intermediate certs in {intermediatecerts_dir}', flush=True)
    if os.path.exists(intermediatecerts_dir):
        for file in os.listdir(intermediatecerts_dir):
            file_path = os.path.join(intermediatecerts_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)


def completeMSPSetup(org_msp_dir):
    src = os.path.join(org_msp_dir, 'cacerts')
    dst = os.path.join(org_msp_dir, 'tlscacerts')

    if not os.path.exists(dst):
        copytree(src, dst)

    # intermediate cacert management
    if os.path.exists(os.path.join(org_msp_dir, 'intermediatecerts')):
        # no intermediate cert in this config, delete generated files for not seeing warning
        removeIntermediateCerts(os.path.join(org_msp_dir, 'intermediatecerts'))

        # uncomment if using intermediate certs
        # copytree(org_msp_dir + '/intermediatecerts/', org_msp_dir + '/tlsintermediatecerts/')


def configLocalMSP(org, user_name):
    user = org['users'][user_name]
    org_user_home = user['home']
    org_user_msp_dir = os.path.join(org_user_home, 'msp')

    # if local admin msp does not exist, create it by enrolling user
    if not os.path.exists(org_user_msp_dir):
        print('Enroll user and copy in admincert for configtxgen', flush=True)

        # wait ca certfile exists before enrolling
        dowait(f"{org['ca']['name']} to start",
               90,
               org['ca']['logfile'],
               [org['ca']['certfile']['internal']])

        msg = f"Enrolling user '{user['name']}' for organization {org['name']} with {org['ca']['host']} and home directory {org_user_home}..."
        print(msg, flush=True)

        # admincerts is required for configtxgen binary
        return enrollWithFiles(user, org, org_user_msp_dir, admincerts=True)


def enrollCABootstrapAdmin(org):

    waitPort(f"{org['ca']['name']} to start",
             90,
             org['ca']['logfile'],
             org['ca']['host'],
             org['ca']['port']['internal'])
    print(f"Enrolling with {org['ca']['name']} as bootstrap identity ...", flush=True)

    org_user_msp_dir = os.path.join(org['users']['bootstrap_admin']['home'], 'msp')
    bootstrap_admin = enrollWithFiles(org['users']['bootstrap_admin'], org, org_user_msp_dir, admincerts=False)
    return bootstrap_admin

    # following commented code is better, but it is easier to save bootstrap_admin cert/key for not working with fabric-sdk-py.
    # TODO: deplace bootstrap_admin outside the users dict of the organization

    # # create ca-cert.pem file
    # target = f"https://{org['ca']['host']}:{org['ca']['port']['internal']}"
    # cacli = ca_service(target=target,
    #                    ca_certs_path=org['ca']['certfile'],
    #                    ca_name=org['ca']['name'])
    # bootstrap_admin = cacli.enroll(org['users']['bootstrap_admin']['name'], org['users']['bootstrap_admin']['pass'])
    # return bootstrap_admin


def registerOrdererIdentities(org):
    badmin = enrollCABootstrapAdmin(org)

    for orderer in org['orderers']:
        print(f"Registering {orderer['name']} with {org['ca']['name']}", flush=True)
        badmin.register(orderer['name'], orderer['pass'], 'orderer', maxEnrollments=-1)

    if 'peers' in org:
        for peer in org['peers']:
            print(f"Registering {peer['name']} with {org['ca']['name']}\n", flush=True)
            badmin.register(peer['name'], peer['pass'], 'peer', maxEnrollments=-1)

    print(f"Registering admin identity with {org['ca']['name']}", flush=True)
    attrs = [{'admin': 'true:ecert'}]
    badmin.register(org['users']['admin']['name'], org['users']['admin']['pass'], maxEnrollments=-1, attrs=attrs)


def registerPeerIdentities(org):
    badmin = enrollCABootstrapAdmin(org)
    for peer in org['peers']:
        print(f"Registering {peer['name']} with {org['ca']['name']}\n", flush=True)
        badmin.register(peer['name'], peer['pass'], 'peer', maxEnrollments=-1)

    print(f"Registering admin identity with {org['ca']['name']}", flush=True)
    # The admin identity has the "admin" attribute which is added to ECert by default
    attrs = [
        {'hf.Registrar.Roles': 'client'},
        {'hf.Registrar.Attributes': '*'},
        {'hf.Revoker': 'true'},
        {'hf.GenCRL': 'true'},
        {'admin': 'true:ecert'},
        {'abac.init': 'true:ecert'}
    ]
    badmin.register(org['users']['admin']['name'], org['users']['admin']['pass'], maxEnrollments=-1, attrs=attrs)

    print(f"Registering user identity with {org['ca']['name']}\n", flush=True)
    if 'user' in org['users']:
        badmin.register(org['users']['user']['name'], org['users']['user']['pass'], maxEnrollments=-1)


def registerIdentities(conf):
    if conf['type'] == 'client':
        registerPeerIdentities(conf)
    if conf['type'] == 'orderer':
        registerOrdererIdentities(conf)


def registerUsers(conf):
    print('Getting CA certificates ...\n', flush=True)

    org_admin_msp_dir = os.path.join(conf['users']['admin']['home'], 'msp')

    if conf['type'] == 'client':
        # will create admin and user folder with an msp folder and populate it. Populate admincerts for configtxgen to work
        # https://hyperledger-fabric.readthedocs.io/en/release-1.2/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp

        # enroll admin and create admincerts
        enrollmentAdmin = configLocalMSP(conf, 'admin')
        # needed for tls communication for create channel from peer for example, copy tlscacerts from cacerts
        completeMSPSetup(org_admin_msp_dir)

        # enroll user and create admincerts
        configLocalMSP(conf, 'user')
    if conf['type'] == 'orderer':
        # https://hyperledger-fabric.readthedocs.io/en/release-1.2/msp.html?highlight=admincerts#msp-setup-on-the-peer-orderer-side
        # https://stackoverflow.com/questions/48221810/what-is-difference-between-admincerts-and-signcerts-in-hyperledge-fabric-msp
        # will create admincerts for configtxgen to work

        # enroll admin and create admincerts
        enrollmentAdmin = configLocalMSP(conf, 'admin')
        # create tlscacerts directory and remove intermediatecerts if exists
        completeMSPSetup(org_admin_msp_dir)

    return enrollmentAdmin


def writeFile(filename, content):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'wb') as f:
        f.write(content)


def saveMSP(msp_dir, enrollment, admincerts=False):
    # cert
    filename = os.path.join(msp_dir, 'signcerts', 'cert.pem')

    writeFile(filename, enrollment._cert)

    # private key
    if enrollment._private_key:
        private_key = enrollment._private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                            format=serialization.PrivateFormat.PKCS8,
                                                            encryption_algorithm=serialization.NoEncryption())
        filename = os.path.join(msp_dir, 'keystore', 'key.pem')
        writeFile(filename, private_key)

    # ca
    filename = os.path.join(msp_dir, 'cacerts', 'ca.pem')
    writeFile(filename, enrollment._caCert)

    if admincerts:
        filename = os.path.join(msp_dir, 'admincerts', 'cert.pem')
        writeFile(filename, enrollment._cert)


def enrollWithFiles(user, org, msp_dir, csr=None, profile='', attr_reqs=None, admincerts=False):
    target = f"https://{org['ca']['host']}:{org['ca']['port']['internal']}"
    cacli = ca_service(target=target,
                       ca_certs_path=org['ca']['certfile']['internal'],
                       ca_name=org['ca']['name'])
    enrollment = cacli.enroll(user['name'], user['pass'], csr=csr, profile=profile, attr_reqs=attr_reqs)

    saveMSP(msp_dir, enrollment, admincerts=admincerts)

    return enrollment


def genTLSCert(node, org, cert_file, key_file, ca_file):
    # Generate our key
    pkey = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend())

    name = org['csr']['names'][0]
    # Generate a CSR
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        # Provide various details about who we are.
        x509.NameAttribute(NameOID.COUNTRY_NAME, name['C']),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, name['ST']),
        x509.NameAttribute(NameOID.LOCALITY_NAME, name['L']),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, name['O']),
        x509.NameAttribute(NameOID.COMMON_NAME, node['host']),
    ])).add_extension(
        # Describe what sites we want this certificate for.
        x509.SubjectAlternativeName([
              # Describe what sites we want this certificate for.
                x509.DNSName(node['host']),
            ]),
        critical=False,
        # Sign the CSR with our private key.
    ).sign(pkey, hashes.SHA256(), default_backend())

    target = f"https://{org['ca']['host']}:{org['ca']['port']['internal']}"
    cacli = ca_service(target=target,
                       ca_certs_path=org['ca']['certfile']['internal'],
                       ca_name=org['ca']['name'])
    enrollment = cacli.enroll(node['name'], node['pass'], csr=csr, profile='tls')

    # cert
    writeFile(cert_file, enrollment._cert)

    # private key
    private_key = pkey.private_bytes(encoding=serialization.Encoding.PEM,
                                     format=serialization.PrivateFormat.PKCS8,
                                     encryption_algorithm=serialization.NoEncryption())
    writeFile(key_file, private_key)

    # ca
    writeFile(ca_file, enrollment._caCert)


def generateGenesis(conf):
    print(f"Generating orderer genesis block at {conf['misc']['genesis_bloc_file']['external']}", flush=True)

    # Note: For some unknown reason (at least for now) the block file can't be
    # named orderer.genesis.block or the orderer will fail to launch

    # configtxgen -profile OrgsOrdererGenesis -channelID substrasystemchannel -outputBlock /substra/data/genesis/genesis.block
    call(['configtxgen',
          '-profile', 'OrgsOrdererGenesis',
          '-channelID', conf['misc']['system_channel_name'],
          '-outputBlock', conf['misc']['genesis_bloc_file']['external']])

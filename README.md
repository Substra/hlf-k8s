# Substra network

This project demonstrates how you can set multiples organizations for dealing with the hyperledger project.
It is composed of at most 3 organizations : orderer, owkin and chu-nantes (optional).

The orderer organization contains an orderer instance named orderer1.
The owkin and chu-nantes organizations have each one 2 peers named peer1 and peer2.

Each organization has a root ca instance for dealing with the users.

> :warning: This project is under active development. Please, wait some times before using it...

## License

This project is developed under the Apache License, Version 2.0 (Apache-2.0), located in the [LICENSE](./LICENSE) file.

## Launch

### Run using doker-compose

#### Bootstrap

Run the `bootstrap.sh` script.
:warning: If you are on linux and want to play with the substra-backend project, please read its documentation first.

It will pull from the hyperledger registry the right docker images and then will build our own docker images from it.

#### Test

Create at the root of your system a `substra` folder with your user rights:

```sh
$> sudo mkdir /substra
$> sudo chown guillaume:guillaume /substra
```

Replace `guillaume:guillaume` by your `user:group`.

> Please make sure that substra-chaincode code is cloned and present beside substra-network project directory

```sh
$> python3 python-scripts/start.py --no-backup
```

- For launching it with a configuration file, pass the `--config` or `-c` option. By default `python-scripts/conf/2orgs.py` will be used
- For launching a network from scratch,  without ising backup files, use `--no-backup` option (recommended in development mode).
- For loading fixtures, pass the `--fixtures` or `-f` option. This is equivalent to an e2e test.
- For revoking an user, pass the `--revoke` or `-r` option. This will revoke user-owkin and try to make a query as a revoked user.

Roughly speaking, it will generate several docker-compose files in /substra/dockerfiles, build the network and run init config.

The `run` docker container will create channel, make peers joins channel, install chaincode and instantiate chaincode.
The `fixtures` docker instance container will create some objectives, algo, datamanager, train data samples, test data samples, traintuples, testtuples on orgs.
The `revoke` docker instance allow you to revoke an user, and query with an expected `access denied` response.

You now will be able to play with the network ! :tada:

:warning: Debugging: Make sure you have set a file named `substra-network.pth` in your virtualenv `lib/python3.6/site-packages` folder containing the absolute path to `substra-network/python-scripts` for being able to run fixtures scripts manually.

#### Network

The docker-compose use the `net_substra` private network for running its docker, if you want to be able to enroll, invoke or query the ledger from the outside, you will have to modify your `/etc/hosts` file on your machine for mapping your localhost:

`/etc/hosts` file:

```sh
127.0.0.1       rca-owkin            # one or two org(s) setup
127.0.0.1       rca-chu-nantes       # two orgs setup
127.0.0.1       rca-orderer
127.0.0.1       peer1-owkin          # one or two org(s) setup
127.0.0.1       peer2-owkin          # one or two org(s) setup
127.0.0.1       peer1-chu-nantes     # two orgs setup
127.0.0.1       peer2-chu-nantes     # two orgs setup
127.0.0.1       orderer1-orderer
127.0.0.1       substra-backend.owkin.xyz substra-frontend.owkin.xyz         # one or two org(s) setup
127.0.0.1       substra-backend.chunantes.xyz substra-frontend.chunantes.xyz # two orgs setup
```

Do not hesitate to reboot your machine for updating your new modified hosts values.
When adding a new organization, for example `clb`, do not forget to add it too

#### Operations

You can see metrics with prometheus or statsd.
Borrowed from this tutorial: <https://medium.com/@jushuspace/hyperledger-fabric-monitoring-with-prometheus-and-statsd-f43ef0ab110e>

##### prometheus

You can run a prometheus server with:

```sh
cd /tmp
curl -O https://raw.githubusercontent.com/prometheus/prometheus/master/documentation/examples/prometheus.yml
docker run -d --name prometheus-server -p 9090:9090  --restart always  -v /tmp/prometheus-2.7.1.linux-amd64/prometheus.yml:/prometheus.yml  prom/prometheus --config.file=/prometheus.yml
docker network connect net_substra prometheus-server
```

then head to `http://localhost:9090/`.

###### statsd

Modify calls to `create_core_config` and `create_orderer_config` in `config_utils.py` with `metrics='statsd'`  
You can run a stats server with:

```sh
docker run -d --name graphite --restart=always -p 80:80 -p 2003-2004:2003-2004 -p 2023-2024:2023-2024 -p 8125:8125/udp -p 8126:8126 graphiteapp/graphite-statsd
docker network connect net_substra graphite
```

then head to `http://localhost/`.

### Run using skaffold

#### Running a custom version of the chaincode

By default, the `skaffold dev` command will start a substra network that uses the default [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode).

To use a custom chaincode locally, change the `chaincodes.src` values in [`skaffold.yaml`](./skaffold.yaml) to point to your local clone of the [substra-chaincode](https://github.com/SubstraFoundation/substra-chaincode), e.g.

- `deploy.helm.realease.name[network-peer-1].setValues.chaincodes[0].src: /home/johndoe/code/substra-chaincode`
- `deploy.helm.realease.name[network-peer-2].setValues.chaincodes[0].src: /home/johndoe/code/substra-chaincode`

The chaincode path must be accessible from your kubernetes cluster:

- On Docker for Mac, go to Settings > File Sharing and make sure the chaincode folder is included in the mounted folders
- On a running minikube instance, run `nohup minikube mount <chaincode-absolute-path>:<chaincode-absolute-path> &`

## substra-backend

A backend is available named substra-backend which can interact with this ledger.

Follow the instructions in the substra-backend project for being able to query/invoke the ledger with the setup created by the run container.

## Fabric SDK PY Debug

Mount a volume to your modified version of fabric-sdk-py in the run container for debugging:
`"$HOME/{PATH_TO_FABRIC_SDK_PY}/fabric-sdk-py/hfc:/usr/local/lib/python3.6/dist-packages/hfc"`

### Hyperledger fabric binaries

You can debug peer and orderer binaries with breakpoints thanks to GoLand from jetbrains.
For being sure to have the correct vendoring on the fabric project.
Make sure you have clone the fabric project in the `src` folder inside your `GOPATH`.
Delete vendoring and regenerate them with:

```sh
$> govendor init && govendor add +external
```

You will then be able to debug the go binaries. If you already launch a network, you can stop a peer:

```sh
$> docker stop peer1-owkin
```

Then create a directory named `/tmp/hyperledger/production` which will contains the backup of the `/var/hyperldger/production`.  
Modify the `core.yaml` for pointing to `/tmp/hyperledger/production` instead of `/var/hyperldger/production`.  
Create also a `/etc/hyperledger/fabric` folder and copy all needed files.  
Usually:

`/etc/hyperledger/fabric/tls/server`  
`/etc/hyperledger/fabric/tls/client`  
`/etc/hyperledger/fabric/msp`  
`/etc/hyperledger/fabric/core.yaml`  
`/etc/hyperledger/fabric/ca/ca-cert.pem`  

You can check the produced dockerfiles for more information.
 

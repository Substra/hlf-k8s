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

### Bootstrap

Run the `bootstrap.sh` script.
:warning: If you are on linux and want to play with the substrabac projects, please read its documentation first.

It will pull from the hyperledger registry the right docker images and then will build our own docker images from it.

### Test

Create at the root of your system a `substra` folder with your user rights:
```bash
$> sudo mkdir /substra
$> sudo chown guillaume:guillaume /substra
```
Replace `guillaume:guillaume` by your `user:group`.


!> Please make sure that substra-chaincode code is cloned and present beside substra-network project directory

```
$> python3 python-scripts/start.py  --no-backup
```

:warning:
Launching `start.py` without the config option, will make a call of `python3 python-scripts/conf/2orgs.py` internally.

- For launching a network from scratch,  without ising backup files, use `--no-backup` option (recommended in development mode).
- For loading fixtures, pass the `--fixtures` or `-f` option. This is equivalent to an e2e test.
- For revoking an user, pass the `--revoke` or `-r` option. This will revoke user-owkin and try to make a query as a revoked user.

Roughly speaking, it will generate several docker-compose files in /substra/docker-files, build the network and run init config.

The `run` docker container will create channel, make peers joins channel, install chaincode and instantiate chaincode.
The `fixtures` docker instance container will create some objectives, algo, datamanager, train data, test data, traintuples on orgs.
The `revoke` docker instance allow you to revoke an user.

You now will be able to play with the network ! :tada:

:warning: Debugging: Make sure you have set a file named `substra-network.pth` in your virtualenv `lib/python3.6/site-packages` folder containing the absolute path to `substra-network/python-scripts` for being able to run fixtures scripts manually.


### Network

The docker-compose use the `net_substra` private network for running its docker, if you want to be able to enroll, invoke or query the ledger from the outside, you will have to modify your `/etc/hosts` file on your machine for mapping your localhost:

`/etc/hosts` file:
```shell
127.0.0.1       rca-owkin            # one or two org(s) setup
127.0.0.1       rca-chu-nantes       # two orgs setup
127.0.0.1       rca-orderer
127.0.0.1       peer1-owkin          # one or two org(s) setup
127.0.0.1       peer2-owkin          # one or two org(s) setup
127.0.0.1       peer1-chu-nantes     # two orgs setup
127.0.0.1       peer2-chu-nantes     # two orgs setup
127.0.0.1       orderer1-orderer
127.0.0.1       owkin.substrabac     # one or two org(s) setup
127.0.0.1       chunantes.substrabac # two orgs setup
```

Do not hesitate to reboot your machine for updating your new modified hosts values.

### substrabac

A backend is available named substrabac which can interact with this ledger.

Follow the instructions in the substrabac project for being able to query/invoke the ledger with the setup created by the run container.

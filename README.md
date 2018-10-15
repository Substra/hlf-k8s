# Substra network

This project demonstrates how you can set multiples organizations for dealing with the hyperledger project.
It is composed of 3 organizations : orderer, owkin and chu-nantes.

The orderer organization contains an orderer instance named orderer1.
The owkin and chu-nantes organizations have each one 2 peers named peer1 and peer2.

Each organization has a root ca instance for dealing with the users.

> :warning: This project is under active development. Please, wait some times before using it...

## License

This project is developed under the Apache License, Version 2.0 (Apache-2.0), located in the [LICENSE](./LICENSE) file.

## Launch

### get docker images

Run the `bootstrap.sh` script.  
:warning: If you are on linux and want to play with the substrabac projects, please read its documentation first. 

It will pull from the hyperledger registry the right docker images and then will build our own docker images from it.

### Test

Go inside the `python-scripts` folder and run:

`python start.py`

It will build the network and run init config.

The `run` docker container will create channel, make peers joins channel, install chaincode and instantiate chaincode.  
The `fixtures` docker instance container will create some challenges, algo, dataset, train data, test data, traintuples on both orgs : owkin and chu-nantes. It is commented by default. Uncomment it in `docker-compose.yaml` for testing and debugging.   
The `revoke` docker instance allow you to revoke an user, Recommandation is to leave this undocumented  

If you do not want to init the chaincode and make queries, comment the run docker part in the docker-compose.

You now will be able to play with the network ! :tada:

### Network

The docker-compose use the `net_substra` private network for running its docker, if you want to be able to enroll, invoke or query the ledger from the outside, you will have to modify your `/etc/hosts` file on your machine for mapping your localhost:

`/etc/hosts` file:
```shell
127.0.0.1       rca-owkin
127.0.0.1       rca-chu-nantes
127.0.0.1       rca-orderer
127.0.0.1       peer1-owkin
127.0.0.1       peer2-owkin
127.0.0.1       peer1-chu-nantes
127.0.0.1       peer2-chu-nantes
127.0.0.1       orderer1-orderer
127.0.0.1       owkin.substrabac
127.0.0.1       chunantes.substrabac
```

Do not hesitate to reboot your machine for updating your new modified hosts values.

### substrabac

A backend is available named substrabac which can interact with this ledger.

Two choices : 

- [RECOMMENDED] Follow the instructions in the substrabac project for being able to query/invoke the ledger with the data created by the run container.


- You'll have to modify the rights of the `data` created folder after running the `./start.py` file with the current user you are executing `substrabac` or simply copy needed files, usually conf files and msp folders generated, then modify the `core.yaml` file in substrabac for having correlated data.

    In my case:
    ```shell
    sudo chown -R guillaume:guillaume ./data
    ```

    Make sure you have correctly set your `/etc/hosts`file too.
    
    You are ready to use the substrabac backend with this ledger network.

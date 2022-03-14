# SENG 468 Software System Scalability Project (Quadra Day Trading)
**Spring 2022**

## Team Members
Anton Nikitenko

Nicole Udy

## Introduction
Quadra Day Trading is the term project that implements the specification detailed [here](https://www.ece.uvic.ca/~seng468/CourseProject.pdf). 

## Pre-requisites
The system runs on Ubuntu 18/20. The following must be installed:
 * Docker version 19.03.6
 * Python3
 * Pip3

## Install and Run
Install dependencies in `requirements.txt` to install docker-compose:

```bash
pip3 install -r requirements.txt
```

Ensure any running instances of `mongod` are sttopped such that port `27017` is available:

```bash
docker-compose up
```

## Set-up Mongo Database

When first running the application, we must ensure that the Mongo DB 
cluster is setup correctly. After running `docker-compose up`, perform the 
following steps:

1. Connect to cfgsvr1 by executing `mongo mongodb://127.0.0.1:40001`.
2. In the container, initialize the replica set for config servers:
```bash
rs.initiate({_id: "cfgrs", configsvr: true, members: [{_id: 0, host: "cfgsvr1"}, {_id: 1, host: "cfgsvr2"}, {_id: 2, host: "cfgsvr3"}]})
```
3. Log out, and connect to shard1svr1 by executing `mongo mongodb://127.0.0.1:50001`.
4. In the container, initialize the replica set for shard 1:
```bash
rs.initiate({_id: "shard1rs", members: [{_id: 0, host: "shard1svr1"}, {_id: 1, host: "shard1svr2"}, {_id: 2, host: "shard1svr3"}]})
```
5. Log out, and connect to shard2svr1 by executing `mongo mongodb://50004`.
6. In the container, initialize the replica set for shard 2:
```bash
rs.initiate({_id: "shard2rs", members: [{_id: 0, host: "shard2svr1"}, {_id: 1, host: "shard2svr2"}, {_id: 2, host: "shard2svr3"}]})
```
7. Then, log in to mongos1 router by executing `mongo mongodb://60000`.
8. In the container, execute the following commands:
```bash
sh.addShard("shard1rs/shard1svr1,shard1svr2,shard1svr3")
sh.addShard("shard2rs/shard2svr1,shard2svr2,shard2svr3")
sh.enableSharding("day_trading")
```
To shard the `accounts` and `pending_transactions`:
```bash
sh.shardCollection("day_trading.accounts", {userid: "hashed"})
sh.shardCollection("day_trading.pending_transactions", {userid: "hashed"})
```
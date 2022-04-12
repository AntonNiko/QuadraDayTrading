# SENG 468 Software System Scalability Project (Quadra Day Trading)
**Spring 2022**

## Team Members
Anton Nikitenko
Nicole Udy

## Introduction
Quadra Day Trading is the term project that implements the specification detailed [here](https://www.ece.uvic.ca/~seng468/CourseProject.pdf). This Readme document
also serves as the documentation for the system.

## Pre-requisites
The system runs on Ubuntu 18/20. The following must be installed:
 * Docker version 19.03.6
 * Python3
 * Pip3

## Install and Run
1. Ensure the following tools are installed so that dependencies are satisfied:
* `setuptools-rust`: Install with pip3
Then, upgrade pip3 by running `pip3 install --upgrade pip`.


2. Install dependencies in `requirements.txt` to install docker-compose:

```bash
pip3 install -r requirements.txt
```

3. Provide permissions to the Redis cache volume by chmod'ing the shared volume to 777:
```bash
sudo chmod 777 redis/
```

4. Ensure any running instances of `mongod` are stopped such that port `27017` is available:

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

## Hardware Requirements

This application runs on an Ubuntu 18/20 operating system (processor difference is irrelevant). For the purposes of this project, our hardware
requirements include a physical machine on which this application can be run, and optionally a virtual machine (e.g. Virtual Box or VMWare) which
can run the application on top of a separate operating system like Windows or macOS. The development of this application was done mostly on a physical 
machine with the following performance specifications:

* AMD Ryzen 7 3800X 8-Core Processor 3.90GHz
* 32.0GB RAM
* Ubuntu 20.04 Virtual Box environment with 100GB SSD storage allocated
* Full connectivity to the internet to download and manage package dependencies

As noted in the performance specifications, the physical hardware must be connected to the internet in order to install, configure, and manage packages such
as APT packages and PIP packages. This network connectivity may be achieved either on bare-metal by being connected with Wi-Fi or wired ethernet cable, or by 
configuring a bridged network adapter in the case of Virtual Box. Furthermore, access to a console is necessary to run and test the application. If a monitor 
attached to the machine is not available, it may be necessary to setup an SSH connection from another machine on the same local network in order to run the 
application.

## Programming tools, Libraries, Platform

As noted in the report portion of this project, we used several tools to help alleviate development difficulties throughout the duration of this project:

* **Version Control**: Git, hosted on GitHub as a public repository accessible by all team members. This allows distributed development and an integrated location where code reviews and tests can be performed
* **IDE**: By default we may use any text editor which allows us to develop and test code efficiently. We will mainly use VSCode as it is a lightweight application which allows plugins to be installed that are relevant to our application. If an IDE is not available, we will default to using applications such as nano or Vim to edit code.
* **Programming Languages**: Python is our main development language due to its simple syntax and large number of libraries. Although it is slower than Java or C#, due to it being an interpreted language, we do not expect significant bottleneck issues.
* **Testing Tools**: Python’s unittest library is well suited to test and validate our system’s behavior at a component level, for unit and integration tests. In order to perform end-to-end tests with all the system’s components at once, we consider using Python as well to interact with the web application and/or inject workloads to be executed. Python also allows us to easily extract metrics from tests, such as runtime errors & exceptions, and performance metrics. The Test Plan section details the strategy behind testing the system. We also plan to use K6 to perform load testing on our application.

## Architecture (Schema and UML)

We provide the following images to illustrate the architecture of the project and how dependencies interact with each other. The UML System Components Diagram provides an illustration of the interfaces that must be created and used:

![UML1](/images/system_components_diagram.png)

The transaction server UML class diagram shows in a general fashion how the transaction server was built to process incoming requests:

![UML2](/images/transaction_server_uml.png)

Finally, the UML system deployment diagram is a visualization of the placement of the final artifacts of the project (i.e. the containers and external interfaces) when they are being executed in a run time environment.

![UML3](/images/uml_system_deployment_diagram.png)

## Project Timeline

The following timeline shows the milestones that we completed through the duration of this project:

| **Date** | **Event/Deliverable** | **Notes** |
| ---------- | ----------- | ---------- |
| Feb 2nd, 2022 | SDS - Report I | Initial revision of SDS before prototyping and implementation |
| Feb 2nd, 2022 | Presentation I | Initial presentation summarizing Report I contents |
| Mar 16th, 2022 | SDS - Report II | Revision of SDS |
| Mar 16th, 2022 | Individual Contribution Report | | 
| Apr 6th, 2022 | Final Presentation | |
| Apr 13th, 2022 | SDS - Final Report | Final version of the SDS report reflecting the final implementation of the system |
| Apr 13th, 2022 | Completed Project Source & Documentation | Submit code with instructions to run, Github link, and any accompanying documentation |

## Team Member Responsibility

The following are the responsibilities each team member had for the duration of the project:

| **Team Member** | **Responsibilities** |
| --------------- | -------------------- |
| Nicole Udy | System Testing (unit/integration/end-to-end, Security measures, User Interface, Database Development and Deployment, Project write-ups |
| Anton Nikitenko | Development of Transaction Server, Containerization and scalability of server, Continuous Integration (CI), Web Application, Project write-ups, Logfile generation |

## Scalability Analysis and Fault Tolerance
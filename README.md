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
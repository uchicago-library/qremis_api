# qremis_api 

## About

A web API for managing a qremis "database".

Information about the qremis specification is available [here](https://github.com/bnbalsamo/qremis)

The supporting python library for qremis is available [here](https://github.com/bnbalsamo/pyqremis)

## Installation / Running

### via docker-compose

```
# docker-compose up
```


### via flask Debug server

Run a dev server with the following command:
```
$ QREMIS_API_CONFIG=$(pwd)/config.py sh debug.sh
```

The included config.py assumes you're running a redis instance listening on localhost on
port 6379, and want to use db 0.

If you have docker you can fire one of these up with
```
# docker run -p 6379:6379 redis
```

The included Dockerfile will build the application in a container, which means the
container must have access to the redis instance referenced in the config.

## Endpoints

### /

#### GET

TODO

### /object_list

#### GET

TODO

#### POST

TODO

### /object_list/<identifier>

#### GET

TODO

### /object_list/<identifier>/linkedRelationships

#### GET

TODO

#### POST

TODO

### /event_list

#### GET

TODO

#### POST

TODO

### /event_list/<identifier>

#### GET

TODO

### /event_list/<identifier>/linkedRelationships

#### GET

TODO

#### POST

TODO

### /agent_list

#### GET

TODO

#### POST

TODO

### /agent_list/<identifier>

#### GET

TODO

### /agent_list/<identifier>/linkedRelationships

#### GET

TODO

#### POST

TODO

### /rights_list

#### GET

TODO

#### POST

TODO

### /rights_list/<identifier>

#### GET

TODO

## /rights_list/<identifier>/linkedRelationships

#### GET

TODO

#### POST

TODO

### /relationship_list

#### GET

TODO

#### POST

TODO

### /relationship_list/<identifier>

#### GET

TODO

### /relationship_list/<identifier>/linkedObjects

#### GET

TODO

#### POST

TODO

### /relationship_list/<identifier>/linkedEvents

#### GET

TODO

#### POST

TODO

### /relationship_list/<identifier>/linkedAgents

#### GET

TODO

#### POST

TODO

### /relationship_list/<identifier>/linkedRights

#### GET

TODO

#### POST

TODO


Author: balsamo@uchicago.edu

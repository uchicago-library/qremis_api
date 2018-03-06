# qremis_api 
[![Build Status](https://travis-ci.org/uchicago-library/qremis_api.svg?branch=master)](https://travis-ci.org/uchicago-library/qremis_api) [![Coverage Status](https://coveralls.io/repos/github/uchicago-library/qremis_api/badge.svg?branch=master)](https://coveralls.io/github/uchicago-library/qremis_api?branch=master) 

v0.0.2

## About

A web API for managing a qremis "database".

Information about the qremis specification is available [here](https://github.com/uchicago-library/qremis)

The supporting python library for qremis is available [here](https://github.com/uchicago-library/pyqremis)

## Configuration
The Qremis_API is configured via environmental variables.

Variable explanations:

- QREMIS_API_STORAGE_BACKEND
    - Specifies which storage backend to use, either redis or mongo
- QREMIS_API_SECRET_KEY
    - Provides the secret key
- QREMIS_API_MONGO_HOST
    - The hostname or ip of the host running the mongo backend
- QREMIS_API_MONGO_PORT
    - The port the mongo daemon is listening on on the MONGO_HOST
    - Defaults to 27017
- QREMIS_API_MONGO_DBNAME
    - The name of the database to use for mongo storage 
- QREMIS_API_REDIS_HOST
    - The hostname or ip of the host running the redis backend
- QREMIS_API_REDIS_PORT
    - The port the redis daemon is listening on on the REDIS_HOST
    - Defaults to 6379
- QREMIS_API_REDIS_DB
    - The name of the database to use for the redis storage
    - Defaults to 0
- QREMIS_API_VERBOSITY
    - Logging verbosity
    - Defaults to WARN
- QREMIS_API_DEFER_CONFIG
    - Prevents configuration from occuring on import
    - Defaults to False

## Installation / Running

### via docker-compose

```
# docker-compose up
```

### via flask Debug server

Utilizing a dev redis server running on localhost as a backend:
```
$ QREMIS_API_STORAGE_BACKEND="redis" QREMIS_API_REDIS_HOST="localhost" ./debug.sh
```

Utilizing a dev mongo server running on localhost as a backend:
```
$ QREMIS_API_STORAGE_BACKEND="mongo" QREMIS_API_MONGO_HOST="localhost" QREMIS_API_MONGO_DBNAME="dev" ./debug.sh
```

## Endpoints

### /

#### GET

##### Returns

```
{
    "object_list": API.url_for(ObjectList),
    "event_list": API.url_for(EventList),
    "agent_list": API.url_for(AgentList),
    "rights_list": API.url_for(RightsList),
    "relationship_list": API.url_for(RelationshipList)
}
```

---

### /object_list

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns

```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "object_list": [
        {"id": the object identifier,
         "_link": API.url_for(Object, id=the object id)}
        for each object in the list
    ]
}
```

#### POST

##### args
- record: The object record to add, as a json str

##### Returns

```
{
    "_link" = API.url_for(Object, id=objId),
    "id": The added object identifier
}
```

---

### /object_list/\<identifier\>

#### GET

```
the qremis record
```

---

### /object_list/\<identifier\>/linkedRelationships

#### GET
##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "linkingRelationshipIdentifier_list": [
        {"id": the linked relationship identifier,
         "_link": a link to the relationship in the API}
        for each relationship linked from the object
    ]
}
```

#### POST

##### args
- relationship_id: The id of a relationship to link to the object

##### Returns
```
the linked identifier
```


---

### /event_list

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "event_list": [
        {"id": the event identifier,
         "_link": API.url_for(Event, id=the event id)}
        for each event in the list
    ]
}
```

#### POST

##### args
- record: The event record to add, as a json str

##### Returns

```
{
    "_link" = API.url_for(Event, id=eventId),
    "id": The added event identifier
}
```

---

### /event_list/\<identifier\>

#### GET

```
the qremis record
```

---

### /event_list/\<identifier\>/linkedRelationships

#### GET
##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "linkingRelationshipIdentifier_list": [
        {"id": the linked relationship identifier,
         "_link": a link to the relationship in the API}
        for each relationship linked from the object
    ]
}
```

#### POST

##### args
- relationship_id: The id of a relationship to link to the object

##### Returns
```
the linked identifier
```

---

### /agent_list

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns

```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "agent_list": [
        {"id": the agent identifier,
         "_link": API.url_for(Agent, id=the agent id)}
        for each agent in the list
    ]
}
```

#### POST

##### args
- record: The agent record to add, as a json str

##### Returns

```
{
    "_link" = API.url_for(Agent, id=agentID),
    "id": The added agent identifier
}
```

---

### /agent_list/\<identifier\>

#### GET

```
the qremis record
```

---

### /agent_list/\<identifier\>/linkedRelationships


#### GET
##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "linkingRelationshipIdentifier_list": [
        {"id": the linked relationship identifier,
         "_link": a link to the relationship in the API}
        for each relationship linked from the object
    ]
}
```

#### POST

##### args
- relationship_id: The id of a relationship to link to the object

##### Returns
```
the linked identifier
```

---

### /rights_list

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns

```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "rights_list": [
        {"id": the rights identifier,
         "_link": API.url_for(Rights, id=the rights id)}
        for each rights in the list
    ]
}
```

#### POST

##### args
- record: The rights record to add, as a json str

##### Returns

```
{
    "_link" = API.url_for(Rights, id=rightsID),
    "id": The added rights identifier
}
```

---

### /rights_list/\<identifier\>

#### GET

```
the qremis record
```

---

## /rights_list/\<identifier\>/linkedRelationships


#### GET
##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "linkingRelationshipIdentifier_list": [
        {"id": the linked relationship identifier,
         "_link": a link to the relationship in the API}
        for each relationship linked from the object
    ]
}
```

#### POST

##### args
- relationship_id: The id of a relationship to link to the object

##### Returns
```
the linked identifier
```

---

### /relationship_list

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "relationship_list": [
        {"id": the relationship identifier,
         "_link": API.url_for(Relationship, id=the relationship id)}
        for each relationship in the list
    ]
}
```

#### POST

##### args
- record: The relationship record to add, as a json str

##### Returns

```
{
    "_link" = API.url_for(Relationship, id=relationshipId),
    "id": The added relationship identifier
}
```

---

### /relationship_list/\<identifier\>

#### GET

```
the qremis record
```

---

### /relationship_list/\<identifier\>/linkedObjects

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "object_list": [
        {"id": the object identifier,
         "_link": API.url_for(Object, id=the object id)}
        for each object in the list
    ]
}
```

#### POST

##### args
- object_id: The id of a object to link to the relationship

##### Returns
```
the linked identifier
```

---

### /relationship_list/\<identifier\>/linkedEvents

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "event_list": [
        {"id": the event identifier,
         "_link": API.url_for(Event, id=the event id)}
        for each event in the list
    ]
}
```

#### POST

##### args
- event_id: The id of a event to link to the relationship

##### Returns
```
the linked identifier
```

---

### /relationship_list/\<identifier\>/linkedAgents

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "agent_list": [
        {"id": the agent identifier,
         "_link": API.url_for(Agent, id=the agent id)}
        for each agent in the list
    ]
}
```

#### POST

##### args
- agent_id: The id of a agent to link to the relationship

##### Returns
```
the linked identifier
```

---

### /relationship_list/\<identifier\>/linkedRights

#### GET

##### kwargs
- cursor ("0"): A cursor to begin the listing at
- limit (1000): A number of object listings to return

##### Returns
```
{
    "starting_cursor": The cursor at which the listing began,
    "next_cursor": The cursor for starting at listing at the
                   next element in the list, or None if the 
                   end of the list has been reached,
    "limit": The limit to the number of listings,
    "rights_list": [
        {"id": the rights identifier,
         "_link": API.url_for(Rights, id=the rights id)}
        for each rights in the list
    ]
}
```

#### POST

##### args
- rights_id: The id of a rights to link to the relationship

##### Returns
```
the linked identifier
```



Author: balsamo@uchicago.edu

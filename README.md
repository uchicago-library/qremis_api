In development

A web API for managing a qremis "database".

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

TODO: Whip up a docker-compose which includes both the redis instance and the
application container in a single network.

Author: balsamo@uchicago.edu

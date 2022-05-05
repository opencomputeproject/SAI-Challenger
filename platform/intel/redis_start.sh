#!/usr/bin/env bash
#
# Script to start Redis using supervisord
#

if [ $(pgrep -x tofino-model | wc -l) = "1" ]; then
    killall -q tofino-model;
fi

exec /usr/bin/redis-server /etc/redis/redis.conf \
    --bind  127.0.0.1 --port 6379 --unixsocket /var/run/redis/redis.sock \
    --pidfile /var/run/redis/redis.pid

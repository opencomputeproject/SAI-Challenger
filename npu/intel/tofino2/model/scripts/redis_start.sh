#!/usr/bin/env bash
#
# Script to start Redis using supervisord
#

if [ $(pgrep -x tofino-model | wc -l) = "1" ]; then
    killall -q tofino-model
fi

exec /usr/bin/redis-server /etc/redis/redis.conf \
    $@ --unixsocket /var/run/redis/redis.sock \
    --pidfile /var/run/redis/redis.pid

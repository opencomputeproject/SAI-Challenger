#!/usr/bin/env bash
#
# Script to start Redis using supervisord
#

if [ $(pgrep -x syncd | wc -l) = "1" ]; then
    killall -q syncd
fi

if [ $(pgrep -x saiserver | wc -l) = "1" ]; then
    killall -q saiserver
fi

exec /usr/bin/redis-server /etc/redis/redis.conf \
    $@ --unixsocket /var/run/redis/redis.sock \
    --pidfile /var/run/redis/redis.pid

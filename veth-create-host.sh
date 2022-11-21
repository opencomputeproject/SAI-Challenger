#! /bin/bash

# Usage: ./veth-create-host.sh DOCKER_1_NAME [DOCKER_2_NAME]

# The script creates veth pairs to connect 2 docker nodes (client and server).
# The 1st docker must use separate netns (which is the default docker behavior).
# The 2d docker can use separate or host netns. The last option is useful when
# you run SAI-Challenger client with HW DUT or the external test equipment that
# requires network connectivity. In that case you need just skip the second argument of the script.

DOCKER1=$1
DOCKER2=$2

if [ -z $DOCKER1 ]; then
    echo "Server Docker name must be specified."
    exit 1
fi

if [ ! -d /var/run/netns ]; then
    mkdir -p /var/run/netns
fi

PID=$(docker inspect --format '{{ .State.Pid }}' $DOCKER1)
DOCKER1_NETNS="$DOCKER1_$PID"
ln -s /proc/$PID/ns/net /var/run/netns/$DOCKER1_NETNS

if [ ! -z $DOCKER2 ]; then
    PID=$(docker inspect --format '{{ .State.Pid }}' $DOCKER2)
    DOCKER2_NETNS="$DOCKER2_$PID"
    ln -s /proc/$PID/ns/net /var/run/netns/$DOCKER2_NETNS
fi

for num in {1..32}; do
    ip link add veth"$num" type veth peer name eth"$num" netns $DOCKER1_NETNS
    ip netns exec $DOCKER1_NETNS ip link set eth"$num" up
    ip link set veth"$num" up
    if [ ! -z $DOCKER2 ]; then
        ip link set dev veth"$num" netns $DOCKER2_NETNS
        ip netns exec $DOCKER2_NETNS ip link set veth"$num" up
    fi
done

#! /bin/bash

# Configure FPs and CPU interface
for num in {1..32} 133; do
    ip link add eth"$num" type veth peer name veth"$num"
    ip link set eth"$num" mtu 10240 up
    ip link set veth"$num" mtu 10240 up
done

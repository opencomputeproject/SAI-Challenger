#! /bin/bash

# Configure FPs
for num in {1..32}; do
    ip link add eth"$num" type veth peer name veth"$num"
    ip link set eth"$num" up
    ip link set veth"$num" up
done

# Configure CPU interface
intf0="eth133"
intf1="eth134"
ip link add $intf0 type veth peer name $intf1
ip link set dev $intf0 mtu 10240 up
ip link set dev $intf1 mtu 10240 up

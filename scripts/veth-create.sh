#! /bin/bash

for num in {1..32}; do
    ip link add eth"$num" type veth peer name veth"$num"
    ip link set eth"$num" up
    ip link set veth"$num" up
done


#! /bin/bash

DONE=0
# Wait for the last 32th interface.
# veth-create-host.sh adds interfaces starting from 1 to 32.
IFACE=eth32

while [ $DONE -eq 0 ]; do
   ip l show dev $IFACE && DONE=1
   sleep 1
done

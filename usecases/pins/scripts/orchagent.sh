#!/usr/bin/env bash

if [ "$MAC_ADDRESS" == "None" ] || [ -z "$MAC_ADDRESS" ]; then
    MAC_ADDRESS=$(ip link show eth0 | grep ether | awk '{print $2}')
    logger "Mac address not found in Device Metadata, Falling back to eth0"
fi

# Create a folder for SwSS record files
mkdir -p /var/log/swss
ORCHAGENT_ARGS="-d /var/log/swss "

# Set orchagent pop batch size to 8192
ORCHAGENT_ARGS+="-b 8192 "

# Set synchronous mode if it is enabled in CONFIG_DB
ORCHAGENT_ARGS+="-s "

ORCHAGENT_ARGS+="-m $MAC_ADDRESS"

exec /usr/local/bin/orchagent ${ORCHAGENT_ARGS}

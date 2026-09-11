
#!/bin/bash
set -e

PORT_COUNT=32
SONIC_VPP_IFMAP="/usr/share/sonic/hwsku/sonic_vpp_ifmap.ini"
VPP_INIT_CLI="/etc/vpp/init.cli"
MTU=9100


sysctl -w net.ipv6.conf.default.disable_ipv6=1

# Creating veth pairs in Linux
for num in $(seq 1 $PORT_COUNT); do
    ip link delete eth"$num" 2>/dev/null || true
    ip link add eth"$num" type veth peer name veth"$num"
    ip link set dev eth"$num" mtu $MTU
    ip link set dev veth"$num" mtu $MTU
    ip link set eth"$num" up
    ip link set veth"$num" up
done

# Generating the SONiC-to-VPP interface mapping
mkdir -p "$(dirname "$SONIC_VPP_IFMAP")"
> "$SONIC_VPP_IFMAP"

for num in $(seq 1 $PORT_COUNT); do
    echo "Ethernet${num} host-eth${num}" >> "$SONIC_VPP_IFMAP"
done

# Generating CLI commands for VPP
mkdir -p "$(dirname "$VPP_INIT_CLI")"
> "$VPP_INIT_CLI"


# Create host-interfaces
for num in $(seq 1 $PORT_COUNT); do
    echo "create host-interface name eth${num}" >> "$VPP_INIT_CLI"
    echo "set interface state host-eth${num} up" >> "$VPP_INIT_CLI"
done

for iface in $(ip -o link show | awk -F': ' '{print $2}' | cut -d@ -f1 | grep -E '^(eth|veth|Ethernet)[0-9]+$'); do
    sysctl -w net.ipv6.conf.$iface.disable_ipv6=1
done

echo "Network initialization complete."


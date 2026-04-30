import ipaddress
import json
import time

import pytest

from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import send_packet, simple_tcpv6_packet, verify_no_packet, verify_packets, verify_any_packet_any_port


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))


@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()


@pytest.fixture
def port_rif_topology(npu):
    """
    Shared topology fixture: removes ports 0 and 1 from the default VLAN,
    creates a VRF with IPv6 enabled and two port RIFs, then restores
    everything after the test.

    Yields:
        dict with keys: vrf_oid, rif_in, rif_eg
    """
    if len(npu.port_oids) < 2:
        pytest.skip("need at least two ports")

    vrf_oid = None
    rif_oid_in = None
    rif_oid_eg = None

    for idx in range(2):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        npu.remove(npu.dot1q_bp_oids[idx])

    try:
        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true"],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        rif_oid_eg = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[1],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        yield {"vrf_oid": vrf_oid, "rif_in": rif_oid_in, "rif_eg": rif_oid_eg}
    finally:
        if rif_oid_eg is not None:
            npu.remove(rif_oid_eg)
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(2):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_ipv6_host_route(npu, dataplane, port_rif_topology):
    """
    Description:
    Check IPv6 host route forwarding via next hop over port RIFs

    Test scenario:
    1. Remove ports 0 and 1 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0 and egress RIF on port 1 attached to the VRF
    4. Create an IPv6 neighbor entry on egress RIF with destination MAC
    5. Create a next hop pointing to the neighbor
    6. Create a /128 host route via the next hop
    7. Send a TCPv6 packet on port 0 and verify routed packet on port 1 with L2 MAC rewrite and hop limit decremented from 64 to 63
    8. Clean up configuration
    """
    vrf_oid = port_rif_topology["vrf_oid"]
    rif_oid_eg = port_rif_topology["rif_eg"]

    ipv6_host = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    neighbor_mac = "00:11:22:33:44:55"
    inner_src = ipaddress.IPv6Address("2000::1")

    nh_oid = None
    neighbor_obj = None
    route_prefix = None

    try:
        neighbor_key = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_eg,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key, separators=(",", ":")
        )
        npu.create(
            neighbor_obj,
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac],
        )

        nh_oid = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_eg,
            ],
        )

        route_prefix = str(ipaddress.ip_interface((ipv6_host, 128)))
        npu.create_route(route_prefix, vrf_oid, nh_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            pkt = simple_tcpv6_packet(
                eth_dst=router_mac,
                eth_src="00:22:22:22:22:22",
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=64,
            )
            exp_pkt = simple_tcpv6_packet(
                eth_dst=neighbor_mac,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )

            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt, [1])

    finally:
        if route_prefix is not None:
            npu.remove_route(route_prefix, vrf_oid)
        if nh_oid is not None:
            npu.remove(nh_oid)
        if neighbor_obj is not None:
            npu.remove(neighbor_obj)


def test_ipv6_lpm_route(npu, dataplane, port_rif_topology):
    """
    Description:
    Check IPv6 LPM route forwarding via next hop over port RIFs

    Test scenario:
    1. Remove ports 0 and 1 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0 and egress RIF on port 1
    4. Create an IPv6 neighbor and next hop on egress RIF
    5. Create a /64 LPM route via the next hop
    6. Send a TCPv6 packet on port 0 and verify routed packet on port 1
    7. Clean up configuration
    """
    vrf_oid = port_rif_topology["vrf_oid"]
    rif_oid_eg = port_rif_topology["rif_eg"]

    ipv6_host = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    neighbor_mac = "00:11:22:33:44:55"
    inner_src = ipaddress.IPv6Address("2000::1")

    nh_oid = None
    neighbor_obj = None
    route_prefix = None

    try:
        neighbor_key = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_eg,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key, separators=(",", ":")
        )
        npu.create(
            neighbor_obj,
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac],
        )

        nh_oid = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_eg,
            ],
        )

        route_prefix = "1234:5678:9abc:def0::/64"
        npu.create_route(route_prefix, vrf_oid, nh_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            pkt = simple_tcpv6_packet(
                eth_dst=router_mac,
                eth_src="00:22:22:22:22:22",
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=64,
            )
            exp_pkt = simple_tcpv6_packet(
                eth_dst=neighbor_mac,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )

            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt, [1])

    finally:
        if route_prefix is not None:
            npu.remove_route(route_prefix, vrf_oid)
        if nh_oid is not None:
            npu.remove(nh_oid)
        if neighbor_obj is not None:
            npu.remove(neighbor_obj)


def test_ipv6_prefix_lengths(npu, dataplane, port_rif_topology):
    """
    Description:
    Check IPv6 route forwarding for prefix lengths from /128 down to /1

    Test scenario:
    1. Create an IPv6 neighbor and next hop on egress RIF
    2. For each prefix length from /128 to /1:
       a. Create a route with that prefix length
       b. Send a TCPv6 packet on port 0 and verify forwarding on port 1
       c. Remove the route
       d. Verify no packet is forwarded after route removal
    3. Clean up configuration
    """
    vrf_oid = port_rif_topology["vrf_oid"]
    rif_oid_eg = port_rif_topology["rif_eg"]

    ipv6_host = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    neighbor_mac = "00:11:22:33:44:55"
    inner_src = ipaddress.IPv6Address("2000::1")

    nh_oid = None
    neighbor_obj = None

    try:
        neighbor_key = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_eg,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key, separators=(",", ":")
        )
        npu.create(
            neighbor_obj,
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac],
        )

        nh_oid = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_eg,
            ],
        )

        router_mac = None
        pkt = None
        exp_pkt = None
        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()
            pkt = simple_tcpv6_packet(
                eth_dst=router_mac,
                eth_src="00:22:22:22:22:22",
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=64,
            )
            exp_pkt = simple_tcpv6_packet(
                eth_dst=neighbor_mac,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )

        for plen in range(128, 0, -1):
            net = ipaddress.ip_network((ipv6_host, plen), strict=False)
            route_prefix = str(net)
            npu.create_route(route_prefix, vrf_oid, nh_oid)
            try:
                if npu.run_traffic:
                    send_packet(dataplane, 0, pkt)
                    verify_packets(dataplane, exp_pkt, [1])
            finally:
                npu.remove_route(route_prefix, vrf_oid)

            if npu.run_traffic:
                send_packet(dataplane, 0, pkt)
                verify_no_packet(dataplane, exp_pkt, 1)

    finally:
        if nh_oid is not None:
            npu.remove(nh_oid)
        if neighbor_obj is not None:
            npu.remove(neighbor_obj)


def test_ipv6_ecmp_host(npu, dataplane):
    """
    Description:
    Check IPv6 host route forwarding via ECMP group over two port RIFs

    Test scenario:
    1. Remove ports 0, 1 and 2 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0, egress RIF1 on port 1, egress RIF2 on port 2
    4. Create two IPv6 neighbors and two next hops on egress RIFs
    5. Create an ECMP next hop group with both next hops as members
    6. Create a /128 host route via the ECMP group
    7. Send multiple TCPv6 packets on port 0 and verify packets arrive on port 1 or port 2
    8. Clean up configuration
    """
    if len(npu.port_oids) < 3:
        pytest.skip("need at least three ports")

    ipv6_host   = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    neighbor_mac1 = "00:11:22:33:44:55"
    neighbor_mac2 = "00:11:22:33:44:66"
    inner_src   = ipaddress.IPv6Address("2000::1")

    vrf_oid      = None
    rif_oid_in   = None
    rif_oid_eg1  = None
    rif_oid_eg2  = None
    nh_oid1      = None
    nh_oid2      = None
    neighbor_obj1 = None
    neighbor_obj2 = None
    ecmp_oid     = None
    member_oid1  = None
    member_oid2  = None
    route_prefix = None

    try:
        for idx in range(3):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            [
                "SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE",
                "true",
            ],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )
        rif_oid_eg1 = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[1],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )
        rif_oid_eg2 = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[2],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        neighbor_key1 = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_eg1,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj1 = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key1, separators=(",", ":")
        )
        npu.create(
            neighbor_obj1,
            [
                "SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS",
                neighbor_mac1,
            ],
        )

        neighbor_key2 = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_eg2,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj2 = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key2, separators=(",", ":")
        )
        npu.create(
            neighbor_obj2,
            [
                "SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS",
                neighbor_mac2,
            ],
        )

        nh_oid1 = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_eg1,
            ],
        )

        nh_oid2 = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_eg2,
            ],
        )

        ecmp_oid = npu.create(
            SaiObjType.NEXT_HOP_GROUP,
            [
                "SAI_NEXT_HOP_GROUP_ATTR_TYPE",
                "SAI_NEXT_HOP_GROUP_TYPE_ECMP",
            ],
        )

        member_oid1 = npu.create(
            SaiObjType.NEXT_HOP_GROUP_MEMBER,
            [
                "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID",
                ecmp_oid,
                "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID",
                nh_oid1,
            ],
        )
        member_oid2 = npu.create(
            SaiObjType.NEXT_HOP_GROUP_MEMBER,
            [
                "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID",
                ecmp_oid,
                "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID",
                nh_oid2,
            ],
        )

        route_prefix = str(ipaddress.ip_interface((ipv6_host, 128)))
        npu.create_route(route_prefix, vrf_oid, ecmp_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            egress_ports = [1, 2]
            port_count = {1: 0, 2: 0}
            for sport in range(0, 10):
                pkt = simple_tcpv6_packet(
                    eth_dst=router_mac,
                    eth_src="00:22:22:22:22:22",
                    ipv6_dst=str(ipv6_host),
                    ipv6_src=str(inner_src),
                    ipv6_hlim=64,
                    tcp_sport=sport,
                )
                exp_pkt1 = simple_tcpv6_packet(
                    eth_dst=neighbor_mac1,
                    eth_src=router_mac,
                    ipv6_dst=str(ipv6_host),
                    ipv6_src=str(inner_src),
                    ipv6_hlim=63,
                    tcp_sport=sport,
                )
                exp_pkt2 = simple_tcpv6_packet(
                    eth_dst=neighbor_mac2,
                    eth_src=router_mac,
                    ipv6_dst=str(ipv6_host),
                    ipv6_src=str(inner_src),
                    ipv6_hlim=63,
                    tcp_sport=sport,
                )
                send_packet(dataplane, 0, pkt)
                rcv_idx = verify_any_packet_any_port(
                    dataplane, [exp_pkt1, exp_pkt2], egress_ports
                )
                port_count[egress_ports[rcv_idx]] += 1

            assert port_count[1] >= 1
            assert port_count[2] >= 1

    finally:
        if route_prefix is not None and vrf_oid is not None:
            npu.remove_route(route_prefix, vrf_oid)
        if member_oid2 is not None:
            npu.remove(member_oid2)
        if member_oid1 is not None:
            npu.remove(member_oid1)
        if ecmp_oid is not None:
            npu.remove(ecmp_oid)
        if nh_oid2 is not None:
            npu.remove(nh_oid2)
        if nh_oid1 is not None:
            npu.remove(nh_oid1)
        if neighbor_obj2 is not None:
            npu.remove(neighbor_obj2)
        if neighbor_obj1 is not None:
            npu.remove(neighbor_obj1)
        if rif_oid_eg2 is not None:
            npu.remove(rif_oid_eg2)
        if rif_oid_eg1 is not None:
            npu.remove(rif_oid_eg1)
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(3):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_ipv6_ecmp_lpm(npu, dataplane):
    """
    Description:
    Check IPv6 LPM route forwarding via 3-way ECMP group over three port RIFs

    Test scenario:
    1. Remove ports 0, 1, 2 and 3 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0, egress RIFs on ports 1, 2 and 3
    4. Create three IPv6 neighbors and three next hops on egress RIFs
    5. Create an ECMP next hop group with all three next hops as members
    6. Create a /64 LPM route via the ECMP group
    7. Send multiple TCPv6 packets with varied flows on port 0 and verify
       balanced distribution across ports 1, 2 and 3
    8. Clean up configuration
    """
    if len(npu.port_oids) < 4:
        pytest.skip("need at least four ports")

    ipv6_prefix  = "6000:1:1::/64"
    ipv6_dst     = ipaddress.IPv6Address("6000:1:1::1")
    neighbor_macs = ["00:11:22:33:44:55", "00:11:22:33:44:66", "00:11:22:33:44:77"]
    inner_src    = ipaddress.IPv6Address("2000::1")

    vrf_oid      = None
    rif_oid_in   = None
    rif_oid_eg   = [None, None, None]
    neighbor_obj = [None, None, None]
    nh_oid       = [None, None, None]
    ecmp_oid     = None
    member_oid   = [None, None, None]
    route_prefix = None

    try:
        for idx in range(4):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            [
                "SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE",
                "true",
            ],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        for i in range(3):
            rif_oid_eg[i] = npu.create(
                SaiObjType.ROUTER_INTERFACE,
                [
                    "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                    "SAI_ROUTER_INTERFACE_TYPE_PORT",
                    "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                    npu.port_oids[i + 1],
                    "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                    vrf_oid,
                ],
            )

        for i in range(3):
            neighbor_key = {
                "switch_id": npu.switch_oid,
                "rif_id": rif_oid_eg[i],
                "ip_address": str(ipv6_dst),
            }
            neighbor_obj[i] = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
                neighbor_key, separators=(",", ":")
            )
            npu.create(
                neighbor_obj[i],
                [
                    "SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS",
                    neighbor_macs[i],
                ],
            )

            nh_oid[i] = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE",
                    "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP",
                    str(ipv6_dst),
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                    rif_oid_eg[i],
                ],
            )

        ecmp_oid = npu.create(
            SaiObjType.NEXT_HOP_GROUP,
            [
                "SAI_NEXT_HOP_GROUP_ATTR_TYPE",
                "SAI_NEXT_HOP_GROUP_TYPE_ECMP",
            ],
        )

        for i in range(3):
            member_oid[i] = npu.create(
                SaiObjType.NEXT_HOP_GROUP_MEMBER,
                [
                    "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID",
                    ecmp_oid,
                    "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID",
                    nh_oid[i],
                ],
            )

        route_prefix = ipv6_prefix
        npu.create_route(route_prefix, vrf_oid, ecmp_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            max_itrs = 200
            egress_ports = [1, 2, 3]
            port_count = {1: 0, 2: 0, 3: 0}
            min_per_path = max_itrs // 3 * 0.8
            for i in range(max_itrs):
                sport = i
                ipv6_src = str(
                    ipaddress.IPv6Address(int(inner_src) + i)
                )
                pkt = simple_tcpv6_packet(
                    eth_dst=router_mac,
                    eth_src="00:22:22:22:22:22",
                    ipv6_dst=str(ipv6_dst),
                    ipv6_src=ipv6_src,
                    ipv6_hlim=64,
                    tcp_sport=sport,
                    tcp_dport=sport + 1,
                )
                exp_pkt1 = simple_tcpv6_packet(
                    eth_dst=neighbor_macs[0],
                    eth_src=router_mac,
                    ipv6_dst=str(ipv6_dst),
                    ipv6_src=ipv6_src,
                    ipv6_hlim=63,
                    tcp_sport=sport,
                    tcp_dport=sport + 1,
                )
                exp_pkt2 = simple_tcpv6_packet(
                    eth_dst=neighbor_macs[1],
                    eth_src=router_mac,
                    ipv6_dst=str(ipv6_dst),
                    ipv6_src=ipv6_src,
                    ipv6_hlim=63,
                    tcp_sport=sport,
                    tcp_dport=sport + 1,
                )
                exp_pkt3 = simple_tcpv6_packet(
                    eth_dst=neighbor_macs[2],
                    eth_src=router_mac,
                    ipv6_dst=str(ipv6_dst),
                    ipv6_src=ipv6_src,
                    ipv6_hlim=63,
                    tcp_sport=sport,
                    tcp_dport=sport + 1,
                )
                send_packet(dataplane, 0, pkt)
                rcv_idx = verify_any_packet_any_port(
                    dataplane, [exp_pkt1, exp_pkt2, exp_pkt3], egress_ports
                )
                port_count[egress_ports[rcv_idx]] += 1

            assert port_count[1] >= min_per_path
            assert port_count[2] >= min_per_path
            assert port_count[3] >= min_per_path

    finally:
        if route_prefix is not None and vrf_oid is not None:
            npu.remove_route(route_prefix, vrf_oid)
        for i in range(3):
            if member_oid[i] is not None:
                npu.remove(member_oid[i])
        if ecmp_oid is not None:
            npu.remove(ecmp_oid)
        for i in range(3):
            if nh_oid[i] is not None:
                npu.remove(nh_oid[i])
        for i in range(3):
            if neighbor_obj[i] is not None:
                npu.remove(neighbor_obj[i])
        for i in range(3):
            if rif_oid_eg[i] is not None:
                npu.remove(rif_oid_eg[i])
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(4):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_ipv6_lag_route(npu, dataplane):
    """
    Description:
    Check IPv6 route forwarding via next hop over a LAG RIF

    Test scenario:
    1. Remove ports 0, 1 and 2 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0
    4. Create a LAG with ports 1 and 2 as members
    5. Create a RIF on the LAG
    6. Create an IPv6 neighbor and next hop on the LAG RIF
    7. Create a /64 route via the next hop
    8. Send a TCPv6 packet on port 0 and verify packet exits on port 1 or port 2
    9. Clean up configuration
    """
    if len(npu.port_oids) < 3:
        pytest.skip("need at least three ports")

    ipv6_dst    = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    neighbor_mac = "00:11:22:33:44:55"
    inner_src   = ipaddress.IPv6Address("2000::1")

    vrf_oid      = None
    rif_oid_in   = None
    lag_oid      = None
    lag_member1  = None
    lag_member2  = None
    rif_oid_lag  = None
    neighbor_obj = None
    nh_oid       = None
    route_prefix = None

    try:
        for idx in range(3):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true"],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        lag_oid = npu.create(SaiObjType.LAG, [])

        lag_member1 = npu.create(
            SaiObjType.LAG_MEMBER,
            [
                "SAI_LAG_MEMBER_ATTR_LAG_ID",
                lag_oid,
                "SAI_LAG_MEMBER_ATTR_PORT_ID",
                npu.port_oids[1],
            ],
        )
        lag_member2 = npu.create(
            SaiObjType.LAG_MEMBER,
            [
                "SAI_LAG_MEMBER_ATTR_LAG_ID",
                lag_oid,
                "SAI_LAG_MEMBER_ATTR_PORT_ID",
                npu.port_oids[2],
            ],
        )

        rif_oid_lag = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                lag_oid,
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        neighbor_key = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_lag,
            "ip_address": str(ipv6_dst),
        }
        neighbor_obj = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key, separators=(",", ":")
        )
        npu.create(
            neighbor_obj,
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac],
        )

        nh_oid = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_dst),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_lag,
            ],
        )

        route_prefix = "1234:5678:9abc:def0::/64"
        npu.create_route(route_prefix, vrf_oid, nh_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            pkt = simple_tcpv6_packet(
                eth_dst=router_mac,
                eth_src="00:22:22:22:22:22",
                ipv6_dst=str(ipv6_dst),
                ipv6_src=str(inner_src),
                ipv6_hlim=64,
            )
            exp_pkt = simple_tcpv6_packet(
                eth_dst=neighbor_mac,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_dst),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )

            send_packet(dataplane, 0, pkt)
            verify_any_packet_any_port(dataplane, [exp_pkt], [1, 2])

    finally:
        if route_prefix is not None and vrf_oid is not None:
            npu.remove_route(route_prefix, vrf_oid)
        if nh_oid is not None:
            npu.remove(nh_oid)
        if neighbor_obj is not None:
            npu.remove(neighbor_obj)
        if rif_oid_lag is not None:
            npu.remove(rif_oid_lag)
        if lag_member2 is not None:
            npu.remove(lag_member2)
        if lag_member1 is not None:
            npu.remove(lag_member1)
        if lag_oid is not None:
            npu.remove(lag_oid)
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(3):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_ipv6_neighbor_mac_update(npu, dataplane):
    """
    Description:
    Check IPv6 neighbor MAC address update on a VLAN RIF

    Test scenario:
    1. Remove ports 0 and 1 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0 (port RIF)
    4. Create a VLAN 10 and add port 1 as a tagged member
    5. Create a VLAN RIF on VLAN 10
    6. Create an IPv6 neighbor with MAC1 on the VLAN RIF
    7. Create a next hop and a /128 host route
    8. Create a static FDB entry for MAC1 on port 1
    9. Send a TCPv6 packet and verify forwarding to MAC1 on port 1
    10. Update neighbor MAC to MAC2
    11. Verify packet is no longer forwarded to MAC1
    12. Create a static FDB entry for MAC2 on port 1
    13. Send a TCPv6 packet and verify forwarding to MAC2 on port 1
    14. Clean up configuration
    """
    if len(npu.port_oids) < 2:
        pytest.skip("need at least two ports")

    ipv6_host    = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    inner_src    = ipaddress.IPv6Address("2000::1")
    neighbor_mac1 = "00:11:22:33:44:55"
    neighbor_mac2 = "00:11:22:33:44:66"
    vlan_id      = 10

    vrf_oid      = None
    rif_oid_in   = None
    vlan_oid     = None
    vlan_member  = None
    rif_oid_vlan = None
    neighbor_obj = None
    nh_oid       = None
    route_prefix = None
    fdb_entry1   = None
    fdb_entry2   = None
    bp_eg        = None

    try:
        for idx in range(2):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true"],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        vlan_oid = npu.create(
            SaiObjType.VLAN,
            ["SAI_VLAN_ATTR_VLAN_ID", str(vlan_id)],
        )

        bp_eg = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE",
                "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                npu.port_oids[1],
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                "true",
            ],
        )
        npu.dot1q_bp_oids[1] = bp_eg
        vlan_member = npu.create_vlan_member(
            vlan_oid,
            bp_eg,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )

        rif_oid_vlan = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_VLAN",
                "SAI_ROUTER_INTERFACE_ATTR_VLAN_ID",
                vlan_oid,
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        neighbor_key = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_vlan,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key, separators=(",", ":")
        )
        npu.create(
            neighbor_obj,
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac1],
        )

        nh_oid = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_vlan,
            ],
        )

        route_prefix = str(ipaddress.ip_interface((ipv6_host, 128)))
        npu.create_route(route_prefix, vrf_oid, nh_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            pkt = simple_tcpv6_packet(
                eth_dst=router_mac,
                eth_src="00:22:22:22:22:22",
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=64,
            )

            fdb_key1 = {
                "switch_id": npu.switch_oid,
                "mac_address": neighbor_mac1,
                "bv_id": vlan_oid,
            }
            fdb_entry1 = "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
                fdb_key1, separators=(",", ":")
            )
            npu.create(
                fdb_entry1,
                [
                    "SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_STATIC",
                    "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_eg,
                ],
            )

            exp_pkt1 = simple_tcpv6_packet(
                eth_dst=neighbor_mac1,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt1, [1])

            npu.set(
                neighbor_obj,
                ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac2],
            )

            exp_pkt_old = simple_tcpv6_packet(
                eth_dst=neighbor_mac1,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )
            send_packet(dataplane, 0, pkt)
            verify_no_packet(dataplane, exp_pkt_old, 1)

            fdb_key2 = {
                "switch_id": npu.switch_oid,
                "mac_address": neighbor_mac2,
                "bv_id": vlan_oid,
            }
            fdb_entry2 = "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
                fdb_key2, separators=(",", ":")
            )
            npu.create(
                fdb_entry2,
                [
                    "SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_STATIC",
                    "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_eg,
                ],
            )

            exp_pkt2 = simple_tcpv6_packet(
                eth_dst=neighbor_mac2,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt2, [1])

    finally:
        if fdb_entry2 is not None:
            npu.remove(fdb_entry2)
        if fdb_entry1 is not None:
            npu.remove(fdb_entry1)
        if route_prefix is not None and vrf_oid is not None:
            npu.remove_route(route_prefix, vrf_oid)
        if nh_oid is not None:
            npu.remove(nh_oid)
        if neighbor_obj is not None:
            npu.remove(neighbor_obj)
        if rif_oid_vlan is not None:
            npu.remove(rif_oid_vlan)
        if vlan_member is not None:
            npu.remove(vlan_member)
        if bp_eg is not None:
            npu.remove(bp_eg)
        if vlan_oid is not None:
            npu.remove(vlan_oid)
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(2):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_ipv6_neighbor_fdb_ageout(npu, dataplane):
    """
    Description:
    Check IPv6 routing behavior when FDB entry is flushed or aged out on a VLAN RIF

    Test scenario:
    1. Remove ports 0 and 1 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0 and VLAN RIF on VLAN 10 with port 1 as tagged member
    4. Create an IPv6 neighbor, next hop and /128 host route
    5. Create a static FDB entry for neighbor MAC on port 1
    6. Send a TCPv6 packet and verify forwarding
    7. Set SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION to DROP
    8. Flush FDB entries and verify packet is dropped
    9. Recreate static FDB entry and verify forwarding is restored
    10. Set FDB aging time and verify packet is dropped after ageout
    11. Restore switch attributes and clean up configuration
    """
    if len(npu.port_oids) < 2:
        pytest.skip("need at least two ports")

    ipv6_host    = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    inner_src    = ipaddress.IPv6Address("2000::1")
    neighbor_mac = "00:11:22:33:44:55"
    vlan_id      = 10

    vrf_oid      = None
    rif_oid_in   = None
    bp_eg        = None
    vlan_oid     = None
    vlan_member  = None
    rif_oid_vlan = None
    neighbor_obj = None
    nh_oid       = None
    route_prefix = None
    fdb_entry    = None

    try:
        for idx in range(2):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true"],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        vlan_oid = npu.create(
            SaiObjType.VLAN,
            ["SAI_VLAN_ATTR_VLAN_ID", str(vlan_id)],
        )

        bp_eg = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE",
                "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                npu.port_oids[1],
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                "true",
            ],
        )
        npu.dot1q_bp_oids[1] = bp_eg
        vlan_member = npu.create_vlan_member(
            vlan_oid,
            bp_eg,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )

        rif_oid_vlan = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_VLAN",
                "SAI_ROUTER_INTERFACE_ATTR_VLAN_ID",
                vlan_oid,
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        neighbor_key = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_vlan,
            "ip_address": str(ipv6_host),
        }
        neighbor_obj = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key, separators=(",", ":")
        )
        npu.create(
            neighbor_obj,
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_mac],
        )

        nh_oid = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_vlan,
            ],
        )

        route_prefix = str(ipaddress.ip_interface((ipv6_host, 128)))
        npu.create_route(route_prefix, vrf_oid, nh_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            pkt = simple_tcpv6_packet(
                eth_dst=router_mac,
                eth_src="00:22:22:22:22:22",
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=64,
            )
            exp_pkt = simple_tcpv6_packet(
                eth_dst=neighbor_mac,
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(inner_src),
                ipv6_hlim=63,
            )

            fdb_key = {
                "switch_id": npu.switch_oid,
                "mac_address": neighbor_mac,
                "bv_id": vlan_oid,
            }
            fdb_entry = "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
                fdb_key, separators=(",", ":")
            )
            npu.create(
                fdb_entry,
                [
                    "SAI_FDB_ENTRY_ATTR_TYPE",
                    "SAI_FDB_ENTRY_TYPE_STATIC",
                    "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID",
                    bp_eg,
                ],
            )
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt, [1])

            npu.set(
                npu.switch_oid,
                [
                    "SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION",
                    "SAI_PACKET_ACTION_DROP",
                ],
            )
            npu.remove(fdb_entry)
            fdb_entry = None
            send_packet(dataplane, 0, pkt)
            verify_no_packet(dataplane, exp_pkt, 1)

            fdb_entry = "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
                fdb_key, separators=(",", ":")
            )
            npu.create(
                fdb_entry,
                [
                    "SAI_FDB_ENTRY_ATTR_TYPE",
                    "SAI_FDB_ENTRY_TYPE_STATIC",
                    "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID",
                    bp_eg,
                ],
            )
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt, [1])

            npu.set(
                npu.switch_oid,
                ["SAI_SWITCH_ATTR_FDB_AGING_TIME", "1"],
            )
            time.sleep(2)
            send_packet(dataplane, 0, pkt)
            verify_no_packet(dataplane, exp_pkt, 1)

    finally:
        npu.set(
            npu.switch_oid,
            [
                "SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION",
                "SAI_PACKET_ACTION_FORWARD",
            ],
        )
        npu.set(
            npu.switch_oid,
            ["SAI_SWITCH_ATTR_FDB_AGING_TIME", "0"],
        )
        if fdb_entry is not None:
            npu.remove(fdb_entry)
        if route_prefix is not None and vrf_oid is not None:
            npu.remove_route(route_prefix, vrf_oid)
        if nh_oid is not None:
            npu.remove(nh_oid)
        if neighbor_obj is not None:
            npu.remove(neighbor_obj)
        if rif_oid_vlan is not None:
            npu.remove(rif_oid_vlan)
        if vlan_member is not None:
            npu.remove(vlan_member)
        if bp_eg is not None:
            npu.remove(bp_eg)
        if vlan_oid is not None:
            npu.remove(vlan_oid)
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(2):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_ipv6_ecmp_group_member_update(npu, dataplane):
    """
    Description:
    Check IPv6 ECMP group member add and remove behavior

    Test scenario:
    1. Remove ports 0, 1, 2 and 3 from the default VLAN bridge ports
    2. Create a VRF with IPv6 admin state enabled
    3. Create ingress RIF on port 0, egress RIFs on ports 1 and 2
    4. Create two neighbors, two next hops and an ECMP group with two members
    5. Create a /128 host route via the ECMP group
    6. Send packets and verify 2-way distribution across ports 1 and 2
    7. Add a third egress RIF on port 3, neighbor, next hop and ECMP member
    8. Send packets and verify 3-way distribution across ports 1, 2 and 3
    9. Remove the third ECMP member and verify 2-way distribution is restored
    10. Clean up configuration
    """
    if len(npu.port_oids) < 4:
        pytest.skip("need at least four ports")

    ipv6_host     = ipaddress.IPv6Address("1234:5678:9abc:def0:4422:1133:5577:99aa")
    inner_src     = ipaddress.IPv6Address("2000::1")
    neighbor_macs = ["00:11:22:33:44:55", "00:11:22:33:44:66", "00:11:22:33:44:77"]

    vrf_oid       = None
    rif_oid_in    = None
    rif_oid_eg    = [None, None, None]
    neighbor_obj  = [None, None, None]
    nh_oid        = [None, None, None]
    ecmp_oid      = None
    member_oid    = [None, None, None]
    route_prefix  = None

    max_itrs = 200
    min_per_path_2way = max_itrs // 2 * 0.8
    min_per_path_3way = max_itrs // 3 * 0.8

    def build_pkts(router_mac, sport):
        pkt = simple_tcpv6_packet(
            eth_dst=router_mac,
            eth_src="00:22:22:22:22:22",
            ipv6_dst=str(ipv6_host),
            ipv6_src=str(ipaddress.IPv6Address(int(inner_src) + sport)),
            ipv6_hlim=64,
            tcp_sport=sport,
            tcp_dport=sport + 1,
        )
        exp_pkts = [
            simple_tcpv6_packet(
                eth_dst=neighbor_macs[j],
                eth_src=router_mac,
                ipv6_dst=str(ipv6_host),
                ipv6_src=str(ipaddress.IPv6Address(int(inner_src) + sport)),
                ipv6_hlim=63,
                tcp_sport=sport,
                tcp_dport=sport + 1,
            )
            for j in range(len(neighbor_macs))
        ]
        return pkt, exp_pkts

    try:
        for idx in range(4):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        vrf_oid = npu.create(
            SaiObjType.VIRTUAL_ROUTER,
            ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true"],
        )

        rif_oid_in = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[0],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )

        for i in range(2):
            rif_oid_eg[i] = npu.create(
                SaiObjType.ROUTER_INTERFACE,
                [
                    "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                    "SAI_ROUTER_INTERFACE_TYPE_PORT",
                    "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                    npu.port_oids[i + 1],
                    "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                    vrf_oid,
                ],
            )

        for i in range(2):
            neighbor_key = {
                "switch_id": npu.switch_oid,
                "rif_id": rif_oid_eg[i],
                "ip_address": str(ipv6_host),
            }
            neighbor_obj[i] = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
                neighbor_key, separators=(",", ":")
            )
            npu.create(
                neighbor_obj[i],
                ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_macs[i]],
            )
            nh_oid[i] = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE",
                    "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP",
                    str(ipv6_host),
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                    rif_oid_eg[i],
                ],
            )

        ecmp_oid = npu.create(
            SaiObjType.NEXT_HOP_GROUP,
            [
                "SAI_NEXT_HOP_GROUP_ATTR_TYPE",
                "SAI_NEXT_HOP_GROUP_TYPE_ECMP",
            ],
        )
        for i in range(2):
            member_oid[i] = npu.create(
                SaiObjType.NEXT_HOP_GROUP_MEMBER,
                [
                    "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID",
                    ecmp_oid,
                    "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID",
                    nh_oid[i],
                ],
            )

        route_prefix = str(ipaddress.ip_interface((ipv6_host, 128)))
        npu.create_route(route_prefix, vrf_oid, ecmp_oid)

        if npu.run_traffic:
            router_mac = npu.get(
                npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]
            ).value()

            port_count = {1: 0, 2: 0}
            for i in range(max_itrs):
                pkt, exp_pkts = build_pkts(router_mac, i)
                send_packet(dataplane, 0, pkt)
                rcv_idx = verify_any_packet_any_port(
                    dataplane, exp_pkts[:2], [1, 2]
                )
                port_count[rcv_idx + 1] += 1

            assert port_count[1] >= min_per_path_2way, \
                f"Port 1 got {port_count[1]} packets, expected >= {min_per_path_2way}"
            assert port_count[2] >= min_per_path_2way, \
                f"Port 2 got {port_count[2]} packets, expected >= {min_per_path_2way}"

        rif_oid_eg[2] = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_TYPE",
                "SAI_ROUTER_INTERFACE_TYPE_PORT",
                "SAI_ROUTER_INTERFACE_ATTR_PORT_ID",
                npu.port_oids[3],
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID",
                vrf_oid,
            ],
        )
        neighbor_key3 = {
            "switch_id": npu.switch_oid,
            "rif_id": rif_oid_eg[2],
            "ip_address": str(ipv6_host),
        }
        neighbor_obj[2] = "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            neighbor_key3, separators=(",", ":")
        )
        npu.create(
            neighbor_obj[2],
            ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", neighbor_macs[2]],
        )
        nh_oid[2] = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE",
                "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP",
                str(ipv6_host),
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID",
                rif_oid_eg[2],
            ],
        )
        member_oid[2] = npu.create(
            SaiObjType.NEXT_HOP_GROUP_MEMBER,
            [
                "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID",
                ecmp_oid,
                "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID",
                nh_oid[2],
            ],
        )

        if npu.run_traffic:
            port_count = {1: 0, 2: 0, 3: 0}
            for i in range(max_itrs):
                pkt, exp_pkts = build_pkts(router_mac, i)
                send_packet(dataplane, 0, pkt)
                rcv_idx = verify_any_packet_any_port(
                    dataplane, exp_pkts, [1, 2, 3]
                )
                port_count[rcv_idx + 1] += 1

            for port in [1, 2, 3]:
                assert port_count[port] >= min_per_path_3way, \
                    f"Port {port} got {port_count[port]} packets, expected >= {min_per_path_3way}"

        npu.remove(member_oid[2])
        member_oid[2] = None

        if npu.run_traffic:
            port_count = {1: 0, 2: 0}
            for i in range(max_itrs):
                pkt, exp_pkts = build_pkts(router_mac, i)
                send_packet(dataplane, 0, pkt)
                rcv_idx = verify_any_packet_any_port(
                    dataplane, exp_pkts[:2], [1, 2]
                )
                port_count[rcv_idx + 1] += 1

            assert port_count[1] >= min_per_path_2way, \
                f"Port 1 got {port_count[1]} packets, expected >= {min_per_path_2way}"
            assert port_count[2] >= min_per_path_2way, \
                f"Port 2 got {port_count[2]} packets, expected >= {min_per_path_2way}"

    finally:
        if route_prefix is not None and vrf_oid is not None:
            npu.remove_route(route_prefix, vrf_oid)
        for i in range(3):
            if member_oid[i] is not None:
                npu.remove(member_oid[i])
        if ecmp_oid is not None:
            npu.remove(ecmp_oid)
        for i in range(3):
            if nh_oid[i] is not None:
                npu.remove(nh_oid[i])
        for i in range(3):
            if neighbor_obj[i] is not None:
                npu.remove(neighbor_obj[i])
        for i in range(3):
            if rif_oid_eg[i] is not None:
                npu.remove(rif_oid_eg[i])
        if rif_oid_in is not None:
            npu.remove(rif_oid_in)
        if vrf_oid is not None:
            npu.remove(vrf_oid)

        for idx in range(4):
            bp_oid = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE",
                    "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                    npu.port_oids[idx],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                    "true",
                ],
            )
            npu.dot1q_bp_oids[idx] = bp_oid
            npu.create_vlan_member(
                npu.default_vlan_oid,
                bp_oid,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
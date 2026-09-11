# Copyright 2021-present Intel Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import time
from urllib import request

import pytest

from saichallenger.topologies.sai_ptf_topology import topology
from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import (
    send_packet,
    simple_tcp_packet,
    simple_udp_packet,
    verify_no_other_packets,
    verify_packet,
    verify_packet_any_port,
    verify_packets,
)

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))

@pytest.fixture(scope="module", autouse=True)
def register_topology(npu, topology):
    npu._topo = topology
    npu._topo_initialized = False
    npu._topo.setup("l3_advanced")
    yield
    npu._topo.teardown()
 
@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()
        npu._topo_initialized = False
        npu._topo.setup()
        
class TestMultipleRoutes:
    """
    Verify forwarding with multiple route to the same nhop.
    """

    def test_multiple_routes_forward(self, npu, dataplane, topology):
        """
        Verifies that multiple routes pointing to the same next hop correctly
        forward packets when traffic generation is enabled.
        """
        topo = topology
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        src_mac = "00:22:22:22:22:22"
        dst_mac = "00:11:22:33:44:55"
        dev_port10 = 10
        dev_port11 = 11
        nhop_ip = "10.10.10.2"
        route1_ip = "10.10.10.1/32"
        route2_ip = "10.10.10.2/32"
        vrf_oid = topo.default_vrf
        rif_oid = topo.port10_rif
        neighbor_key = npu._neighbor_entry_key(rif_oid, nhop_ip)

        npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac])
        nhop = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP", nhop_ip,
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", rif_oid,
            ],
        )
        npu.create_route(route1_ip, vrf_oid, nhop)
        npu.create_route(route2_ip, vrf_oid, nhop)

        try:
            if npu.run_traffic:
                for route_ip in (route1_ip, route2_ip):
                    pkt = simple_tcp_packet(
                        eth_dst=router_mac,
                        eth_src=src_mac,
                        ip_dst=route_ip.split("/")[0],
                        ip_id=105,
                    )
                    exp_pkt = simple_tcp_packet(
                        eth_dst=dst_mac,
                        eth_src=router_mac,
                        ip_dst=route_ip.split("/")[0],
                        ip_id=105,
                        ip_ttl=63,
                    )

                    send_packet(dataplane, dev_port11, pkt)
                    verify_packet(dataplane, exp_pkt, dev_port10)
        finally:
            npu.remove_route(route1_ip, vrf_oid)
            npu.remove_route(route2_ip, vrf_oid)
            npu.remove(nhop)
            npu.remove(neighbor_key)


class TestDropRoute:
    """
    Verify drop route.
    """
    def test_drop_route(self, npu, dataplane, topology):
        """
        Description:
        Verifies trapped route behavior by checking CPU queue packet counter increment.
        """
        topo = topology
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        src_mac = "00:22:22:22:22:22"
        dst_mac = "00:11:22:33:44:55"
        dev_port11 = 11
        nhop_ip = "10.10.10.2"
        route_ip = "10.10.10.1/32"
        vrf_oid = topo.default_vrf
        rif_oid = topo.port10_rif
        neighbor_key = npu._neighbor_entry_key(rif_oid, nhop_ip)
        route_key = npu._route_entry_key(vrf_oid, route_ip)

        npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac])
        nhop = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP", nhop_ip,
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", rif_oid,
            ],
        )
        npu.create_route(route_ip, vrf_oid, nhop, ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"])

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=router_mac,
                    eth_src=src_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=64,
                )

                cpu_queue = topo._cpu_queue(0)
                pre_stats = topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")

                status, action = npu.get(route_key, ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", ""], False)
                assert status == "SAI_STATUS_SUCCESS"
                assert action.value() == "SAI_PACKET_ACTION_TRAP"

                send_packet(dataplane, dev_port11, pkt)
                verify_no_other_packets(dataplane)
                time.sleep(4)

                post_stats = topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                assert post_stats == pre_stats + 1, (
                    "CPU queue0 packet counters did not increment for route trap: "
                    f"pre={pre_stats}, post={post_stats}"
                )
        finally:
            npu.remove_route(route_ip, vrf_oid)
            npu.remove(nhop)
            npu.remove(neighbor_key)


class TestRouteUpdate:
    """
    Verify correct forwarding after route update.
    """

    def test_route_update(self, npu, dataplane, topology):
        """
        Description:
        Verifies that updating a route's next hop correctly forwards packets to the new destination.
        """
        topo = topology
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        dst_mac_1 = "00:11:22:33:44:55"
        dst_mac_2 = "00:11:22:33:44:66"
        src_mac = "00:22:22:22:22:22"
        dev_port10 = 10
        dev_port11 = 11
        nhop_ip_1 = "10.10.10.2"
        nhop_ip_2 = "10.10.10.3"
        route_ip = "10.10.10.1/32"
        vrf_oid = topo.default_vrf
        rif_oid = topo.port10_rif
        neighbor_key_1 = npu._neighbor_entry_key(rif_oid, nhop_ip_1)
        route_key = npu._route_entry_key(vrf_oid, route_ip)

        npu.create(neighbor_key_1, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac_1])
        nhop_1 = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP", nhop_ip_1,
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", rif_oid,
            ],
        )
        npu.create_route(route_ip, vrf_oid, nhop_1)

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=router_mac,
                    eth_src=src_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_id=105,
                    ip_ttl=64,
                )
                exp_pkt_1 = simple_tcp_packet(
                    eth_dst=dst_mac_1,
                    eth_src=router_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_id=105,
                    ip_ttl=63,
                )
                exp_pkt_2 = simple_tcp_packet(
                    eth_dst=dst_mac_2,
                    eth_src=router_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_id=105,
                    ip_ttl=63,
                )

                send_packet(dataplane, dev_port11, pkt)
                verify_packet(dataplane, exp_pkt_1, dev_port10)

            neighbor_entry_2 = npu._neighbor_entry_key(rif_oid, nhop_ip_2)
            npu.create(
                neighbor_entry_2,
                ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac_2],
            )
            nhop_2 = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP", nhop_ip_2,
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", rif_oid,
                ],
            )
            if npu.run_traffic:
                npu.set(route_key, ["SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID", nhop_2])
                send_packet(dataplane, dev_port11, pkt)
                verify_packet(dataplane, exp_pkt_2, dev_port10)

                npu.set(route_key, ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"])
                send_packet(dataplane, dev_port11, pkt)
                verify_no_other_packets(dataplane, timeout=3)

                npu.set(route_key, ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
                send_packet(dataplane, dev_port11, pkt)
                verify_packet(dataplane, exp_pkt_2, dev_port10)

                npu.set(route_key, ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"])
                cpu_queue = topo._cpu_queue(0)
                pre_stats = topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                send_packet(dataplane, dev_port11, pkt)
                time.sleep(4)
                post_stats = topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                assert post_stats == pre_stats + 1

                npu.set(route_key, ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
                send_packet(dataplane, dev_port11, pkt)
                verify_packet(dataplane, exp_pkt_2, dev_port10)
        finally:
            npu.remove(route_key)
            npu.remove(nhop_2)
            npu.remove(neighbor_entry_2)
            npu.remove(nhop_1)
            npu.remove(neighbor_key_1)


class TestRouteIngressRif:
    """
    Verifies that a route can forward a packet back through its ingress RIF.
    """
    def test_route_ingress_rif(self, npu, dataplane, topology):
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        src_mac = "00:22:22:22:22:22"
        dst_mac = "00:11:22:33:44:55"
        dev_port10 = 10
        nhop_ip = "10.10.10.2"
        route_ip = "10.10.10.1/32"
        vrf_oid = topology.default_vrf
        rif_oid = topology.port10_rif
        neighbor_key = npu._neighbor_entry_key(rif_oid, nhop_ip)

        npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac])
        nhop = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP", nhop_ip,
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", rif_oid,
            ],
        )
        npu.create_route(route_ip, vrf_oid, nhop)

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=router_mac,
                    eth_src=src_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=64,
                )
                exp_pkt = simple_tcp_packet(
                    eth_dst=dst_mac,
                    eth_src=router_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=63,
                )

                send_packet(dataplane, dev_port10, pkt)
                verify_packet(dataplane, exp_pkt, dev_port10)
        finally:
            npu.remove_route(route_ip, vrf_oid)
            npu.remove(nhop)
            npu.remove(neighbor_key)


class TestEmptyEcmpGroup:
    """Verifies that packets routed to an empty ECMP group are dropped."""

    def test_empty_ecmp_group(self, npu, dataplane, topology):
        topo = topology
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        src_mac = "00:22:22:22:22:22"
        dev_port10 = 10
        route_ip = "10.10.10.1/32"
        vrf_oid = topo.default_vrf
        nhop_group = npu.create(
            SaiObjType.NEXT_HOP_GROUP,
            [
                "SAI_NEXT_HOP_GROUP_ATTR_TYPE",
                "SAI_NEXT_HOP_GROUP_TYPE_ECMP",
            ],
        )
        npu.create_route(route_ip, vrf_oid, nhop_group)

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=router_mac,
                    eth_src=src_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=64,
                )

                send_packet(dataplane, dev_port10, pkt)
                verify_no_other_packets(dataplane, timeout=3)
        finally:
            npu.remove_route(route_ip, vrf_oid)
            npu.remove(nhop_group)


class TestSviNeighbor:
    """Verifies routed forwarding through a neighbor on a VLAN SVI."""

    def test_svi_neighbor(self, npu, dataplane, topology):
        topo = topology
        if len(npu.port_oids) <= 26:
            pytest.skip("SviNeighborTest requires physical port indices 24–26 (27 ports)")

        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        src_mac = "00:22:22:22:22:22"
        dev_port10 = 10
        dev_port24 = 24
        vrf_oid = topo.default_vrf
        port_oids = npu.port_oids[24:27]
        dst_macs = [
            "00:11:22:33:44:55",
            "00:22:22:33:44:55",
            "00:33:22:33:44:55",
        ]
        nhop_ips = ["10.10.0.1", "10.10.0.2", "10.10.0.3"]
        route_ips = [
            "10.10.10.1/32",
            "10.10.10.2/32",
            "10.10.10.3/32",
        ]

        bridge_ports = [
            npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", port_oid,
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
                ],
            )
            for port_oid in port_oids
        ]
        vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100"])
        vlan_members = [
            npu.create_vlan_member(vlan_oid, bridge_port, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            for bridge_port in bridge_ports
        ]
        for port_oid in port_oids:
            npu.set(port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])

        vlan_rif = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", vrf_oid,
                "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_VLAN",
                "SAI_ROUTER_INTERFACE_ATTR_VLAN_ID", vlan_oid,
            ],
        )

        neighbor_keys = []
        nhops = []
        for nhop_ip, dst_mac, route_ip in zip(nhop_ips, dst_macs, route_ips):
            neighbor_key = npu._neighbor_entry_key(vlan_rif, nhop_ip)
            npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac])
            nhop = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP", nhop_ip,
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", vlan_rif,
                ],
            )
            npu.create_route(route_ip, vrf_oid, nhop)
            neighbor_keys.append(neighbor_key)
            nhops.append(nhop)

        for dst_mac, bridge_port in zip(dst_macs, bridge_ports):
            npu.create_fdb(vlan_oid, dst_mac, bridge_port)

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=router_mac,
                    eth_src=src_mac,
                    ip_dst=route_ips[0].split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=64,
                )
                exp_pkt = simple_tcp_packet(
                    eth_dst=dst_macs[0],
                    eth_src=router_mac,
                    ip_dst=route_ips[0].split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=63,
                )

                send_packet(dataplane, dev_port10, pkt)
                verify_packets(dataplane, exp_pkt, [dev_port24])
        finally:
            for dst_mac in reversed(dst_macs):
                npu.remove_fdb(vlan_oid, dst_mac)
            for route_ip in reversed(route_ips):
                npu.remove_route(route_ip, vrf_oid)
            for nhop in reversed(nhops):
                npu.remove(nhop)
            for neighbor_key in reversed(neighbor_keys):
                npu.remove(neighbor_key)
            npu.remove(vlan_rif)
            for port_oid in port_oids:
                npu.set(port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
            for vlan_member in reversed(vlan_members):
                npu.remove(vlan_member)
            npu.remove(vlan_oid)
            for bridge_port in reversed(bridge_ports):
                npu.remove_bridge_port(bridge_port)


class TestCpuForward:
    """Verifies route forwarding to the CPU with an IP2ME hostif trap."""
    def test_cpu_forward(self, npu, dataplane, topology):
        topo = topology
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        src_mac = "00:22:22:22:22:22"
        dev_port10 = 10
        route_ip = "10.10.10.1/32"
        vrf_oid = topo.default_vrf
        cpu_port = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_CPU_PORT", "oid:0x0"], False)[1].oid()
        npu.create_route(route_ip, vrf_oid, cpu_port)

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=router_mac,
                    eth_src=src_mac,
                    ip_dst=route_ip.split("/")[0],
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=64,
                )

                send_packet(dataplane, dev_port10, pkt)
                verify_no_other_packets(dataplane, timeout=3)

            trap_group = npu.create(
                "SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP",
                [
                    "SAI_HOSTIF_TRAP_GROUP_ATTR_ADMIN_STATE", "true",
                    "SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE", "4",
                ],
            )
            trap = npu.create(
                "SAI_OBJECT_TYPE_HOSTIF_TRAP",
                [
                    "SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP", trap_group,
                    "SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE", "SAI_HOSTIF_TRAP_TYPE_IP2ME",
                    "SAI_HOSTIF_TRAP_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                ],
            )
            if npu.run_traffic:
                cpu_queue4 = topo._cpu_queue(4)
                pre_stats = topo.get_counter(cpu_queue4, "SAI_QUEUE_STAT_PACKETS")

                send_packet(dataplane, dev_port10, pkt)
                time.sleep(4)

                post_stats = topo.get_counter(cpu_queue4, "SAI_QUEUE_STAT_PACKETS")
                assert post_stats == pre_stats + 1, (
                    "CPU queue4 packet counter did not increment for IP2ME trap: "
                    f"pre={pre_stats}, post={post_stats}"
                )
        finally:
            npu.remove(trap)
            npu.remove(trap_group)
            npu.remove_route(route_ip, vrf_oid)
            

class TestRemoveAddNeighbor:
    """Verifies forwarding, gleaning, and recovery when a neighbor is removed and re-added."""
    def test_remove_add_neighbor(self, npu, dataplane, topology):
        topo = topology
        router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        ipv4_addr = "10.1.1.10"
        mac_addr = "00:10:10:10:10:10"
        dev_port10 = 10
        lag_dev_ports = [17, 18, 19]
        vrf_oid = topo.default_vrf
        rif_oid = topo.lag4_rif
        route_ip = ipv4_addr + "/32"
        neighbor_key = npu._neighbor_entry_key(rif_oid, ipv4_addr)
        npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", mac_addr])
        npu.create_route(route_ip, vrf_oid, rif_oid)

        try:
            if npu.run_traffic:
                pkt = simple_udp_packet(
                    eth_dst=router_mac,
                    ip_dst=ipv4_addr,
                    ip_ttl=64,
                )
                exp_pkt = simple_udp_packet(
                    eth_dst=mac_addr,
                    eth_src=router_mac,
                    ip_dst=ipv4_addr,
                    ip_ttl=63,
                )

                send_packet(dataplane, dev_port10, pkt)
                verify_packet_any_port(dataplane, exp_pkt, lag_dev_ports)

                npu.remove(neighbor_key, False)
                cpu_queue = topo._cpu_queue(0)
                pre_stats = topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                send_packet(dataplane, dev_port10, pkt)
                verify_no_other_packets(dataplane)
                post_stats = topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                assert post_stats == pre_stats + 1, (
                    "CPU queue packet counter did not increment after neighbor removal: "
                    f"pre={pre_stats}, post={post_stats}"
                )

                npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", mac_addr])
                send_packet(dataplane, dev_port10, pkt)
                verify_packet_any_port(dataplane, exp_pkt, lag_dev_ports)
        finally:
            npu.remove_route(route_ip, vrf_oid)
            npu.remove(neighbor_key)


class TestRouteNeighborCollision:
    """Verifies forwarding and CPU gleaning for RIF routes with and without a neighbor."""
    def test_route_neighbor_collision(self, npu, dataplane, topology):
        self.topo = topology
        self.router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        self.src_mac = "00:22:22:22:22:22"
        self.dst_mac = "00:11:22:33:44:55"
        self.dev_port10 = 10
        self.dev_port11 = 11
        self.ip_addr = "10.10.10.1"
        self.route_ip = self.ip_addr + "/32"
        self.vrf_oid = self.topo.default_vrf
        self.rif_oid = self.topo.port10_rif
        self.neighbor_key = npu._neighbor_entry_key(self.rif_oid, self.ip_addr)
        
        npu.create(self.neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dst_mac])
        nhop = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP", self.ip_addr,
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", self.rif_oid,
            ],
        )

        try:
            if npu.run_traffic:
                pkt = simple_tcp_packet(
                    eth_dst=self.router_mac,
                    eth_src=self.src_mac,
                    ip_dst=self.ip_addr,
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=64,
                )
                exp_pkt = simple_tcp_packet(
                    eth_dst=self.dst_mac,
                    eth_src=self.router_mac,
                    ip_dst=self.ip_addr,
                    ip_src="192.168.0.1",
                    ip_id=105,
                    ip_ttl=63,
                )
                cpu_queue = self.topo._cpu_queue(0)

                send_packet(dataplane, self.dev_port11, pkt)
                verify_packets(dataplane, exp_pkt, [self.dev_port10])

                npu.create_route(self.route_ip, self.vrf_oid, self.rif_oid)
                send_packet(dataplane, self.dev_port11, pkt)
                verify_packets(dataplane, exp_pkt, [self.dev_port10])

                npu.remove_route(self.route_ip, self.vrf_oid)
                send_packet(dataplane, self.dev_port11, pkt)
                verify_packets(dataplane, exp_pkt, [self.dev_port10])

                npu.create_route(self.route_ip, self.vrf_oid, self.rif_oid)
                send_packet(dataplane, self.dev_port11, pkt)
                verify_packets(dataplane, exp_pkt, [self.dev_port10])

                npu.remove(self.neighbor_key)
                pre_stats = self.topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                send_packet(dataplane, self.dev_port11, pkt)
                time.sleep(4)
                post_stats = self.topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                assert post_stats == pre_stats + 1, (
                    "CPU queue packet counter did not increment after neighbor removal: "
                    f"pre={pre_stats}, post={post_stats}"
                )

                npu.create(self.neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dst_mac])
                send_packet(dataplane, self.dev_port11, pkt)
                verify_packets(dataplane, exp_pkt, [self.dev_port10])

                npu.remove_route(self.route_ip, self.vrf_oid)
                npu.remove(self.neighbor_key)
                send_packet(dataplane, self.dev_port11, pkt)
                verify_no_other_packets(dataplane)

            npu.create_route(self.route_ip, self.vrf_oid, self.rif_oid)
            if npu.run_traffic:
                pre_stats = self.topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                send_packet(dataplane, self.dev_port11, pkt)
                time.sleep(4)
                post_stats = self.topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
                assert post_stats == pre_stats + 1

                npu.create(self.neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dst_mac])
                send_packet(dataplane, self.dev_port11, pkt)
                verify_packets(dataplane, exp_pkt, [self.dev_port10])
        finally:
            npu.remove(npu._route_entry_key(self.vrf_oid, self.route_ip))
            npu.remove(nhop)
            npu.remove(self.neighbor_key)


class L3DirBcastRouteTestHelper:
    """Shared topology and traffic checks for directed-broadcast route tests."""
    @pytest.fixture(autouse=True)
    def setup_class(self, request, npu, topology):
        topo = topology
        if len(npu.port_oids) <= 25:
            pytest.skip("Directed-broadcast tests require physical port indices 24–25")

        request.cls.topo = topo
        request.cls.router_mac = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_SRC_MAC_ADDRESS"]).value()
        request.cls.dev_port10 = 10
        request.cls.dev_port24 = 24
        request.cls.dev_port25 = 25
        request.cls.vrf_oid = topo.default_vrf
        request.cls.port10_rif = topo.port10_rif
        request.cls.ip_addr1 = "10.10.10.1"
        request.cls.ip_addr1_subnet = "10.10.10.0/24"
        request.cls.dmac1 = "00:11:22:33:44:55"
        request.cls.dir_bcast_ip_addr1 = "10.10.10.255"
        request.cls.dir_bcast_dmac1 = "ff:ff:ff:ff:ff:ff"
        request.cls.ip_addr2 = "20.20.20.1"
        request.cls.ip_addr2_subnet = "20.20.20.0/24"
        request.cls.dmac2 = "22:11:22:33:44:55"
        request.cls.port24_oid = npu.port_oids[24]
        request.cls.port25_oid = npu.port_oids[25]

        request.cls.port24_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", request.cls.port24_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        request.cls.port25_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", request.cls.port25_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        request.cls.vlan100 = npu.create(SaiObjType.VLAN,["SAI_VLAN_ATTR_VLAN_ID", "100"])
        request.cls.vlan100_member1 = npu.create_vlan_member(request.cls.vlan100, request.cls.port24_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        request.cls.vlan100_member2 = npu.create_vlan_member(request.cls.vlan100, request.cls.port25_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(request.cls.port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        npu.set(request.cls.port25_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        npu.create_fdb(
            request.cls.vlan100,
            request.cls.dmac1,
            request.cls.port24_bp,
            entry_type="SAI_FDB_ENTRY_TYPE_STATIC",
            action="SAI_PACKET_ACTION_FORWARD",
        )
        request.cls.vlan100_rif = npu.create(
            SaiObjType.ROUTER_INTERFACE,
            [
                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", request.cls.vrf_oid,
                "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_VLAN",
                "SAI_ROUTER_INTERFACE_ATTR_VLAN_ID", request.cls.vlan100,
            ],
        )

    @pytest.fixture(scope="class", autouse=True)
    def teardown_class(self, request, npu):
        yield
        npu.remove(request.cls.vlan100_rif)
        npu.remove_fdb(request.cls.vlan100, request.cls.dmac1)
        npu.set(request.cls.port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.set(request.cls.port25_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.remove(request.cls.vlan100_member2)
        npu.remove(request.cls.vlan100_member1)
        npu.remove(request.cls.vlan100)
        npu.remove_bridge_port(request.cls.port25_bp)
        npu.remove_bridge_port(request.cls.port24_bp)

    def _verify_cpu_glean(self, dataplane, ingress_port, ip_dst, eth_src):
        pkt = simple_tcp_packet(
            eth_dst=self.router_mac,
            eth_src=eth_src,
            ip_dst=ip_dst,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=64,
        )
        cpu_queue = self.topo._cpu_queue(0)
        pre_stats = self.topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
        send_packet(dataplane, ingress_port, pkt)
        time.sleep(4)
        post_stats = self.topo.get_counter(cpu_queue, "SAI_QUEUE_STAT_PACKETS")
        assert post_stats == pre_stats + 1, (
            "CPU queue packet counter did not increment for directed-route glean: "
            f"pre={pre_stats}, post={post_stats}"
        )

    def traffic_trap_test1(self, dataplane):
        """Verify CPU gleaning for route destinations without neighbors."""
        self._verify_cpu_glean(
            dataplane,
            self.dev_port10,
            self.ip_addr1,
            "00:22:22:22:22:21",
        )
        self._verify_cpu_glean(
            dataplane,
            self.dev_port24,
            self.ip_addr2,
            "00:22:22:22:22:22",
        )

    def traffic_trap_test2(self,  dataplane):
        """Verify CPU gleaning for unresolved hosts within routed subnets."""
        self._verify_cpu_glean(
            dataplane,
            self.dev_port10,
            "10.10.10.2",
            "00:22:22:22:22:21",
        )
        self._verify_cpu_glean(
            dataplane,
            self.dev_port24,
            "20.20.20.2",
            "00:22:22:22:22:22",
        )

    def traffic_test(self, dataplane):
        """Verify unicast and directed-broadcast forwarding."""
        pkt = simple_tcp_packet(
            eth_dst=self.router_mac,
            eth_src="00:22:22:22:22:21",
            ip_dst=self.ip_addr1,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=64,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst=self.dmac1,
            eth_src=self.router_mac,
            ip_dst=self.ip_addr1,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=63,
        )
        send_packet(dataplane, self.dev_port10, pkt)
        verify_packets(dataplane, exp_pkt, [self.dev_port24])

        pkt = simple_tcp_packet(
            eth_dst=self.router_mac,
            eth_src="00:22:22:22:22:22",
            ip_dst=self.dir_bcast_ip_addr1,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=64,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst=self.dir_bcast_dmac1,
            eth_src=self.router_mac,
            ip_dst=self.dir_bcast_ip_addr1,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=63,
        )
        send_packet(dataplane, self.dev_port10, pkt)
        verify_packets(
            dataplane,
            exp_pkt,
            [self.dev_port24, self.dev_port25],
        )

        pkt = simple_tcp_packet(
            eth_dst=self.router_mac,
            eth_src="00:22:22:22:22:23",
            ip_dst=self.ip_addr2,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=64,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst=self.dmac2,
            eth_src=self.router_mac,
            ip_dst=self.ip_addr2,
            ip_src="192.168.0.1",
            ip_id=105,
            ip_ttl=63,
        )
        send_packet(dataplane, self.dev_port25, pkt)
        verify_packets(dataplane, exp_pkt, [self.dev_port10])


class TestDirBcastGleanAndForward(L3DirBcastRouteTestHelper):
    """Verifies CPU gleaning before neighbor resolution and forwarding afterward."""
    def test_directed_broadcast_glean_and_forward(self, npu, dataplane):
        try:
            npu.create_route(self.ip_addr1_subnet, self.vrf_oid, self.vlan100_rif)
            npu.create_route(self.ip_addr2_subnet, self.vrf_oid, self.port10_rif)
            if npu.run_traffic:
                self.traffic_trap_test1(dataplane)
                self.traffic_trap_test2(dataplane)

            neighbor0 = npu._neighbor_entry_key(self.vlan100_rif, self.dir_bcast_ip_addr1)
            npu.create(neighbor0, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dir_bcast_dmac1])

            neighbor1 = npu._neighbor_entry_key(self.vlan100_rif, self.ip_addr1)
            npu.create(neighbor1, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dmac1])
            nhop1 = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP", self.ip_addr1,
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", self.vlan100_rif,
                ],
            )

            neighbor2 = npu._neighbor_entry_key(self.port10_rif, self.ip_addr2)
            npu.create(neighbor2, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dmac2])
            nhop2 = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP", self.ip_addr2,
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", self.port10_rif,
                ],
            )
            if npu.run_traffic:
                self.traffic_test(dataplane)
                self.traffic_trap_test2(dataplane)
        finally:
            npu.remove_route(self.ip_addr1_subnet, self.vrf_oid)
            npu.remove_route(self.ip_addr2_subnet, self.vrf_oid)
            npu.remove(nhop1)
            npu.remove(nhop2)
            npu.remove(neighbor1)
            npu.remove(neighbor2)
            npu.remove(neighbor0)


class TestDirBcastForward(L3DirBcastRouteTestHelper):
    """Verifies directed-broadcast and unicast forwarding with full neighbor/nhop config."""
    def test_directed_broadcast_forward(self, npu, dataplane):
        try:
            neighbor1 = npu._neighbor_entry_key(self.vlan100_rif, self.ip_addr1)
            npu.create(neighbor1, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dmac1])
            nhop1 = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP", self.ip_addr1,
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", self.vlan100_rif,
                ],
            )

            neighbor2 = npu._neighbor_entry_key(self.port10_rif, self.ip_addr2)
            npu.create(neighbor2, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dmac2])
            nhop2 = npu.create(
                SaiObjType.NEXT_HOP,
                [
                    "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                    "SAI_NEXT_HOP_ATTR_IP", self.ip_addr2,
                    "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", self.port10_rif,
                ],
            )

            neighbor0 = npu._neighbor_entry_key(self.vlan100_rif, self.dir_bcast_ip_addr1)
            npu.create(neighbor0, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", self.dir_bcast_dmac1])
            npu.create_route(self.ip_addr1_subnet, self.vrf_oid, self.vlan100_rif)
            npu.create_route(self.ip_addr2_subnet, self.vrf_oid, self.port10_rif)
            if npu.run_traffic:
                self.traffic_test(dataplane)
                self.traffic_trap_test2(dataplane)
        finally:
            npu.remove_route(self.ip_addr1_subnet, self.vrf_oid)
            npu.remove_route(self.ip_addr2_subnet, self.vrf_oid)
            npu.remove(nhop1)
            npu.remove(nhop2)
            npu.remove(neighbor1)
            npu.remove(neighbor2)
            npu.remove(neighbor0)


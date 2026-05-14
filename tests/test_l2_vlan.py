import time

import pytest
from scapy.layers.l2 import Dot1Q

import saichallenger.topologies.sai_ptf_topology
from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import (
    send_packet,
    simple_arp_packet,
    simple_tcp_packet,
    simple_udp_packet,
    verify_each_packet_on_each_port,
    verify_each_packet_on_multiple_port_lists,
    verify_no_other_packets,
    verify_packet,
    verify_packets,
)


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))


@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()


@pytest.fixture(scope="module")
def sai_ptf_topology(npu):
    with saichallenger.topologies.sai_ptf_topology.config(npu) as topo:
        yield topo


def _vlan_data(vlan_id, ports, untagged, large_port):
    return {
        "vlan_id": vlan_id,
        "ports": ports,
        "untagged": untagged,
        "large_port": large_port,
    }


def _flush_dyn_fdb(npu, bv_oid):
    if bv_oid is None:
        return
    npu.flush_fdb_entries(
        npu.switch_oid,
        [
            "SAI_FDB_FLUSH_ATTR_BV_ID", bv_oid,
            "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE",
            "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC",
        ],
    )


def _vlan_stat_names():
    return [
        "SAI_VLAN_STAT_IN_OCTETS", "",
        "SAI_VLAN_STAT_OUT_OCTETS", "",
        "SAI_VLAN_STAT_IN_PACKETS", "",
        "SAI_VLAN_STAT_IN_UCAST_PKTS", "",
        "SAI_VLAN_STAT_OUT_PACKETS", "",
        "SAI_VLAN_STAT_OUT_UCAST_PKTS", "",
    ]


def _vlan_stats_map(npu, vlan_oid):
    return npu.get_stats(vlan_oid, _vlan_stat_names()).counters()


class TestL2Vlan:
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        if len(npu.port_oids) < 32:
            pytest.skip("TestL2Vlan requires at least 32 ports (indices 0..31)")

        request.cls.npu = npu
        request.cls.topo = topo
        request.cls.i_pkt_count = 0
        request.cls.e_pkt_count = 0

        request.cls.vlan10 = topo.vlan10
        request.cls.vlan20 = topo.vlan20
        request.cls.vlan30 = topo.vlan30
        request.cls.default_1q_bridge = topo.default_1q_bridge
        request.cls.switch_id = topo.switch_id

        request.cls.port0 = topo.port0
        request.cls.port1 = topo.port1
        request.cls.port2 = topo.port2
        request.cls.port3 = topo.port3
        request.cls.port24 = npu.port_oids[24]
        request.cls.port25 = npu.port_oids[25]
        request.cls.port26 = npu.port_oids[26]
        request.cls.port27 = npu.port_oids[27]
        request.cls.port28 = npu.port_oids[28]
        request.cls.port29 = npu.port_oids[29]
        request.cls.port30 = npu.port_oids[30]
        request.cls.port31 = npu.port_oids[31]

        request.cls.port0_bp = topo.port0_bp
        request.cls.port1_bp = topo.port1_bp
        request.cls.port2_bp = topo.port2_bp
        request.cls.port3_bp = topo.port3_bp
        request.cls.port20_bp = topo.port20_bp
        request.cls.port21_bp = topo.port21_bp
        request.cls.lag1 = topo.lag1
        request.cls.lag2 = topo.lag2
        request.cls.lag1_bp = topo.lag1_bp
        request.cls.lag2_bp = topo.lag2_bp

        request.cls.mac0 = "00:00:00:00:00:11"
        request.cls.mac1 = "00:00:00:00:00:22"
        request.cls.mac2 = "00:00:00:00:00:33"
        request.cls.mac3 = "00:00:00:00:00:44"

        for i in range(24, 32):
            bp = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", npu.port_oids[i],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
                ],
            )
            setattr(request.cls, "port%d_bp" % i, bp)

        request.cls.vlan10_member3 = npu.create_vlan_member(
            topo.vlan10, request.cls.port24_bp,
            "SAI_VLAN_TAGGING_MODE_UNTAGGED",
        )
        request.cls.vlan10_member4 = npu.create_vlan_member(
            topo.vlan10, request.cls.port25_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )

        npu.set(request.cls.port24, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])

        npu.create_fdb(topo.vlan10, request.cls.mac0, request.cls.port0_bp)
        npu.create_fdb(topo.vlan10, request.cls.mac1, request.cls.port1_bp)
        npu.create_fdb(topo.vlan10, request.cls.mac2, request.cls.port24_bp)
        npu.create_fdb(topo.vlan10, request.cls.mac3, request.cls.port25_bp)

        request.cls.lag10 = npu.create(SaiObjType.LAG, [])
        request.cls.lag_mbr31 = npu.create(
            SaiObjType.LAG_MEMBER,
            [
                "SAI_LAG_MEMBER_ATTR_LAG_ID", request.cls.lag10,
                "SAI_LAG_MEMBER_ATTR_PORT_ID", request.cls.port28,
            ],
        )
        request.cls.lag11 = npu.create(SaiObjType.LAG, [])
        request.cls.lag_mbr41 = npu.create(
            SaiObjType.LAG_MEMBER,
            [
                "SAI_LAG_MEMBER_ATTR_LAG_ID", request.cls.lag11,
                "SAI_LAG_MEMBER_ATTR_PORT_ID", request.cls.port29,
            ],
        )

        request.cls.lag10_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", request.cls.lag10,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        request.cls.lag11_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", request.cls.lag11,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )

        request.cls.vlan40 = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "40"])
        request.cls.vlan_member41 = npu.create_vlan_member(
            request.cls.vlan40, request.cls.port26_bp,
            "SAI_VLAN_TAGGING_MODE_UNTAGGED",
        )
        request.cls.vlan_member42 = npu.create_vlan_member(
            request.cls.vlan40, request.cls.port27_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member43 = npu.create_vlan_member(
            request.cls.vlan40, request.cls.lag10_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member44 = npu.create_vlan_member(
            request.cls.vlan40, request.cls.lag11_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )

        request.cls.vlan50 = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "50"])
        request.cls.vlan_member51 = npu.create_vlan_member(
            request.cls.vlan50, request.cls.port26_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member52 = npu.create_vlan_member(
            request.cls.vlan50, request.cls.port27_bp,
            "SAI_VLAN_TAGGING_MODE_UNTAGGED",
        )
        request.cls.vlan_member53 = npu.create_vlan_member(
            request.cls.vlan50, request.cls.lag10_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member54 = npu.create_vlan_member(
            request.cls.vlan50, request.cls.lag11_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )

        request.cls.vlan60 = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "60"])
        request.cls.vlan_member61 = npu.create_vlan_member(
            request.cls.vlan60, request.cls.port26_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member62 = npu.create_vlan_member(
            request.cls.vlan60, request.cls.port27_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member63 = npu.create_vlan_member(
            request.cls.vlan60, request.cls.lag10_bp,
            "SAI_VLAN_TAGGING_MODE_UNTAGGED",
        )
        request.cls.vlan_member64 = npu.create_vlan_member(
            request.cls.vlan60, request.cls.lag11_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )

        request.cls.vlan70 = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "70"])
        request.cls.vlan_member71 = npu.create_vlan_member(
            request.cls.vlan70, request.cls.port26_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member72 = npu.create_vlan_member(
            request.cls.vlan70, request.cls.port27_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member73 = npu.create_vlan_member(
            request.cls.vlan70, request.cls.lag10_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        request.cls.vlan_member74 = npu.create_vlan_member(
            request.cls.vlan70, request.cls.lag11_bp,
            "SAI_VLAN_TAGGING_MODE_UNTAGGED",
        )

        yield

        npu.set(topo.port2, ["SAI_PORT_ATTR_PORT_VLAN_ID", "20"])

        for bv in (
            request.cls.vlan10,
            request.cls.vlan40,
            request.cls.vlan50,
            request.cls.vlan60,
            request.cls.vlan70,
        ):
            if bv is not None:
                try:
                    npu.flush_fdb_entries(
                        npu.switch_oid,
                        [
                            "SAI_FDB_FLUSH_ATTR_BV_ID", bv,
                            "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE",
                            "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC",
                        ],
                    )
                except Exception:
                    pass

        npu.remove_fdb(request.cls.vlan10, request.cls.mac0)
        npu.remove_fdb(request.cls.vlan10, request.cls.mac1)
        npu.remove_fdb(request.cls.vlan10, request.cls.mac2)
        npu.remove_fdb(request.cls.vlan10, request.cls.mac3)

        npu.set(request.cls.port24, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])

        npu.remove(request.cls.vlan10_member3)
        npu.remove(request.cls.vlan10_member4)

        npu.remove(request.cls.vlan_member41)
        npu.remove(request.cls.vlan_member42)
        npu.remove(request.cls.vlan_member43)
        npu.remove(request.cls.vlan_member44)
        npu.remove(request.cls.vlan_member51)
        npu.remove(request.cls.vlan_member52)
        npu.remove(request.cls.vlan_member53)
        npu.remove(request.cls.vlan_member54)
        npu.remove(request.cls.vlan_member61)
        npu.remove(request.cls.vlan_member62)
        npu.remove(request.cls.vlan_member63)
        npu.remove(request.cls.vlan_member64)
        npu.remove(request.cls.vlan_member71)
        npu.remove(request.cls.vlan_member72)
        npu.remove(request.cls.vlan_member73)
        npu.remove(request.cls.vlan_member74)

        npu.remove(request.cls.lag_mbr31)
        npu.remove(request.cls.lag_mbr41)

        npu.remove(request.cls.lag10_bp)
        npu.remove(request.cls.lag11_bp)

        npu.remove(request.cls.lag10)
        npu.remove(request.cls.lag11)

        npu.remove(request.cls.vlan40)
        npu.remove(request.cls.vlan50)
        npu.remove(request.cls.vlan60)
        npu.remove(request.cls.vlan70)

        npu.remove(request.cls.port31_bp)
        npu.remove(request.cls.port30_bp)
        npu.remove(request.cls.port29_bp)
        npu.remove(request.cls.port28_bp)
        npu.remove(request.cls.port27_bp)
        npu.remove(request.cls.port26_bp)
        npu.remove(request.cls.port25_bp)
        npu.remove(request.cls.port24_bp)

    def _inc_vlan10_ucast(self):
        type(self).i_pkt_count += 1
        type(self).e_pkt_count += 1

    def test_forwarding(self, npu, dataplane):
        """
        Description:
        Basic L2 forwarding on VLAN 10 across access, trunk, and LAG-facing ports.

        Test scenario:
        1. Send known unicast from port0 toward MACs on LAG and trunk ports and verify delivery.
        2. Send tagged traffic from the trunk toward the LAG and access ports with expected tagging.
        3. Increment software VLAN 10 counters on each successful unicast exchange.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        pkt = simple_tcp_packet(
            eth_dst=self.mac2,
            eth_src=self.mac0,
            ip_dst="172.16.0.1",
            ip_id=101,
            ip_ttl=64,
        )
        send_packet(dataplane, 0, pkt)
        verify_packet(dataplane, pkt, 24)
        self._inc_vlan10_ucast()

        pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="172.16.0.1",
            ip_id=102,
            ip_ttl=64,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="172.16.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_id=102,
            ip_ttl=64,
            pktlen=104,
        )
        send_packet(dataplane, 0, pkt)
        verify_packet(dataplane, exp_pkt, 1)
        self._inc_vlan10_ucast()

        pkt = simple_tcp_packet(
            eth_dst=self.mac3,
            eth_src=self.mac1,
            ip_dst="172.16.0.1",
            ip_id=102,
            ip_ttl=64,
            dl_vlan_enable=True,
            vlan_vid=10,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst=self.mac3,
            eth_src=self.mac1,
            ip_dst="172.16.0.1",
            ip_id=102,
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        send_packet(dataplane, 1, pkt)
        verify_packet(dataplane, exp_pkt, 25)
        self._inc_vlan10_ucast()

        pkt = simple_tcp_packet(
            eth_dst=self.mac0,
            eth_src=self.mac1,
            ip_dst="172.16.0.1",
            ip_id=102,
            ip_ttl=64,
            dl_vlan_enable=True,
            vlan_vid=10,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst=self.mac0,
            eth_src=self.mac1,
            ip_dst="172.16.0.1",
            ip_id=102,
            ip_ttl=64,
            pktlen=96,
        )
        send_packet(dataplane, 1, pkt)
        verify_packet(dataplane, exp_pkt, 0)
        self._inc_vlan10_ucast()

    def test_native_vlan(self, npu, dataplane):
        """
        Description:
        Native VLAN behavior on a trunk port and on a tagged LAG using VLANs 10 and 20.

        Test scenario:
        1. Exchange tagged and untagged traffic on VLAN 10 with and without native VLAN rewrites on port1.
        2. Disable learning on VLAN 20, move native VLANs to 20, and verify LAG flooding with a static FDB entry.
        3. Restore port and LAG native VLAN defaults and remove the static FDB entry created for the LAG source MAC.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        fdb20_mac = "00:00:00:00:00:55"
        fdb20_installed = False
        try:
            tag_pkt = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=10,
                ip_ttl=64,
                pktlen=104,
            )
            untag_pkt = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 1, tag_pkt)
            verify_packet(dataplane, tag_pkt, 25)
            self._inc_vlan10_ucast()

            tag_pkt1 = simple_udp_packet(
                eth_dst=self.mac0,
                eth_src=self.mac2,
                dl_vlan_enable=True,
                vlan_vid=10,
                ip_ttl=64,
                pktlen=104,
            )
            untag_pkt1 = simple_udp_packet(
                eth_dst=self.mac0,
                eth_src=self.mac2,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 1, tag_pkt1)
            verify_packet(dataplane, untag_pkt1, 0)
            self._inc_vlan10_ucast()

            send_packet(dataplane, 1, untag_pkt)
            verify_no_other_packets(dataplane, timeout=1)

            tag_pkt_40 = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac2,
                dl_vlan_enable=True,
                vlan_vid=40,
                ip_ttl=64,
                pktlen=104,
            )
            send_packet(dataplane, 1, tag_pkt_40)
            verify_no_other_packets(dataplane, timeout=1)

            self.npu.set(self.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])

            send_packet(dataplane, 1, tag_pkt)
            verify_packet(dataplane, tag_pkt, 25)
            self._inc_vlan10_ucast()

            send_packet(dataplane, 1, tag_pkt1)
            verify_packet(dataplane, untag_pkt1, 0)
            self._inc_vlan10_ucast()

            send_packet(dataplane, 1, untag_pkt)
            verify_packet(dataplane, tag_pkt, 25)
            self._inc_vlan10_ucast()

            send_packet(dataplane, 1, untag_pkt1)
            verify_packet(dataplane, untag_pkt1, 0)
            self._inc_vlan10_ucast()

            send_packet(dataplane, 1, tag_pkt_40)
            verify_no_other_packets(dataplane, timeout=1)

            self.npu.set(self.vlan20, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
            self.npu.set(self.port2, ["SAI_PORT_ATTR_PORT_VLAN_ID", "20"])
            self.npu.set(self.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "20"])

            tag_pkt_20 = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=20,
                ip_ttl=64,
                pktlen=104,
            )
            lag1_ports = [7, 8, 9]
            send_packet(dataplane, 1, untag_pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [tag_pkt_20, untag_pkt, tag_pkt_20],
                [lag1_ports, [2], [3]],
            )

            self.npu.create_fdb(self.vlan20, fdb20_mac, self.lag2_bp)
            fdb20_installed = True

            tag_pkt_lag = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=fdb20_mac,
                dl_vlan_enable=True,
                vlan_vid=20,
                ip_ttl=64,
                pktlen=104,
            )
            untag_pkt_lag = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=fdb20_mac,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 7, untag_pkt_lag)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [untag_pkt_lag, tag_pkt_lag],
                [[2], [3]],
            )

            self.npu.set(self.lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])

            send_packet(dataplane, 1, tag_pkt)
            verify_packet(dataplane, tag_pkt, 25)
            self._inc_vlan10_ucast()

            self.npu.set(self.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])

            send_packet(dataplane, 1, untag_pkt)
            verify_no_other_packets(dataplane, timeout=1)

            send_packet(dataplane, 1, tag_pkt)
            verify_packet(dataplane, tag_pkt, 25)
            self._inc_vlan10_ucast()

        finally:
            self.npu.set(self.port2, ["SAI_PORT_ATTR_PORT_VLAN_ID", "20"], False)
            self.npu.set(self.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            if fdb20_installed:
                self.npu.remove_fdb(self.vlan20, fdb20_mac)
            self.npu.set(self.vlan20, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])
            self.npu.set(self.lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])

    def test_priority_tagging(self, npu, dataplane):
        """
        Description:
        Priority-tagged (VLAN 0) frames on access, LAG, and trunk ports with mixed native VLANs.

        Test scenario:
        1. Install temporary VLAN 20 members and static FDB entries for off-LAG MACs used by the scenario.
        2. Send priority-tagged frames from multiple ingress paths and verify expected VLAN tags on egress.
        3. Toggle native VLAN configuration on port1 and lag2, then remove temporary VLAN members and static FDB keys.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        mac5 = "00:55:55:55:55:55"
        mac6 = "00:66:66:66:66:66"
        mac7 = "00:77:77:77:77:77"
        mac8 = "00:88:88:88:88:88"

        vm1 = self.npu.create_vlan_member(
            self.vlan20, self.port26_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        vm2 = self.npu.create_vlan_member(
            self.vlan20, self.port27_bp,
            "SAI_VLAN_TAGGING_MODE_UNTAGGED",
        )

        self.npu.create_fdb(self.vlan10, mac5, self.lag1_bp)
        self.npu.create_fdb(self.vlan20, mac6, self.lag2_bp)
        self.npu.create_fdb(self.vlan20, mac7, self.port26_bp)
        self.npu.create_fdb(self.vlan20, mac8, self.port27_bp)

        try:
            pkt = simple_udp_packet(
                eth_dst=self.mac2,
                eth_src=self.mac0,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
                pktlen=104,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=self.mac2,
                eth_src=self.mac0,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 0, pkt)
            verify_packet(dataplane, exp_pkt, 24)
            self._inc_vlan10_ucast()

            pkt = simple_udp_packet(
                eth_dst=self.mac1,
                eth_src=self.mac0,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=self.mac1,
                eth_src=self.mac0,
                dl_vlan_enable=True,
                vlan_vid=10,
                ip_ttl=64,
            )
            send_packet(dataplane, 0, pkt)
            verify_packet(dataplane, exp_pkt, 1)
            self._inc_vlan10_ucast()

            pkt = simple_udp_packet(
                eth_dst=self.mac2,
                eth_src=mac5,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
                pktlen=104,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=self.mac2,
                eth_src=mac5,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 4, pkt)
            verify_packet(dataplane, exp_pkt, 24)
            self._inc_vlan10_ucast()

            pkt = simple_udp_packet(
                eth_dst=self.mac1,
                eth_src=mac5,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=self.mac1,
                eth_src=mac5,
                dl_vlan_enable=True,
                vlan_vid=10,
                ip_ttl=64,
            )
            send_packet(dataplane, 4, pkt)
            verify_packet(dataplane, exp_pkt, 1)
            self._inc_vlan10_ucast()

            pkt = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            send_packet(dataplane, 1, pkt)
            verify_no_other_packets(dataplane, timeout=1)

            pkt = simple_udp_packet(
                eth_dst=self.mac0,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            send_packet(dataplane, 1, pkt)
            verify_no_other_packets(dataplane, timeout=1)

            pkt = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=mac6,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            send_packet(dataplane, 7, pkt)
            verify_no_other_packets(dataplane, timeout=1)

            pkt = simple_udp_packet(
                eth_dst=self.mac0,
                eth_src=mac6,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            send_packet(dataplane, 7, pkt)
            verify_no_other_packets(dataplane, timeout=1)

            self.npu.set(self.lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "20"])
            self.npu.set(self.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])

            pkt = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=10,
                ip_ttl=64,
            )
            send_packet(dataplane, 1, pkt)
            verify_packet(dataplane, exp_pkt, 25)
            self._inc_vlan10_ucast()

            pkt = simple_udp_packet(
                eth_dst=mac7,
                eth_src=mac6,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=mac7,
                eth_src=mac6,
                dl_vlan_enable=True,
                vlan_vid=20,
                ip_ttl=64,
            )
            send_packet(dataplane, 7, pkt)
            verify_packet(dataplane, exp_pkt, 26)

            pkt = simple_udp_packet(
                eth_dst=self.mac0,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
                pktlen=104,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=self.mac0,
                eth_src=self.mac1,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 1, pkt)
            verify_packet(dataplane, exp_pkt, 0)
            self._inc_vlan10_ucast()

            pkt = simple_udp_packet(
                eth_dst=mac8,
                eth_src=mac6,
                dl_vlan_enable=True,
                vlan_vid=0,
                ip_ttl=64,
                pktlen=104,
            )
            exp_pkt = simple_udp_packet(
                eth_dst=mac8,
                eth_src=mac6,
                ip_ttl=64,
                pktlen=100,
            )
            send_packet(dataplane, 7, pkt)
            verify_packet(dataplane, exp_pkt, 27)

        finally:
            self.npu.set(self.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])
            self.npu.remove_fdb(self.vlan10, mac5)  # FIX A
            self.npu.remove_fdb(self.vlan20, mac6)  # FIX A
            self.npu.remove_fdb(self.vlan20, mac7)  # FIX A
            self.npu.remove_fdb(self.vlan20, mac8)  # FIX A
            self.npu.remove(vm1)
            self.npu.remove(vm2)

    def test_pv_drop(self, npu, dataplane):
        """
        Description:
        Port-VLAN discard for disallowed VLANs and IF_IN_VLAN_DISCARDS accounting on the access port.

        Test scenario:
        1. Send VLAN 100 and untagged frames from the trunk toward port0 and expect drops when VLAN 10 is not carried.
        2. Send valid VLAN 10 traffic and confirm forwarding to the trunk.
        3. Send VLAN 11 traffic from the access port and assert the VLAN discard counter increments by one.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        v100_pkt = simple_tcp_packet(
            eth_dst=self.mac0,
            eth_src=self.mac1,
            dl_vlan_enable=True,
            vlan_vid=100,
            ip_dst="10.0.0.1",
            ip_ttl=64,
        )
        untagged_pkt = simple_tcp_packet(
            eth_dst=self.mac0,
            eth_src=self.mac1,
            ip_dst="10.0.0.1",
            ip_ttl=64,
        )
        v10_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        exp_at_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        v11_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=11,
            ip_ttl=64,
        )

        send_packet(dataplane, 1, v100_pkt)
        verify_no_other_packets(dataplane, timeout=1)

        send_packet(dataplane, 1, untagged_pkt)
        verify_no_other_packets(dataplane, timeout=1)

        send_packet(dataplane, 0, v10_pkt)
        verify_packet(dataplane, exp_at_pkt, 1)
        self._inc_vlan10_ucast()

        pre = self.npu.get_stats(
            self.port0,
            ["SAI_PORT_STAT_IF_IN_VLAN_DISCARDS", ""],
        ).counters()
        if_in_vlan_discards_pre = pre["SAI_PORT_STAT_IF_IN_VLAN_DISCARDS"]

        send_packet(dataplane, 0, v11_pkt)
        verify_no_other_packets(dataplane, timeout=1)

        post = self.npu.get_stats(
            self.port0,
            ["SAI_PORT_STAT_IF_IN_VLAN_DISCARDS", ""],
        ).counters()
        if_in_vlan_discards = post["SAI_PORT_STAT_IF_IN_VLAN_DISCARDS"]
        assert if_in_vlan_discards_pre + 1 == if_in_vlan_discards

    def test_lag_pv_miss(self, npu, dataplane):
        """
        Description:
        Port-VLAN filtering on an untagged LAG for VLANs that are not the LAG native VLAN.

        Test scenario:
        1. Program static FDB entries so MACs resolve on VLAN 20 and VLAN 40 from the LAG.
        2. Forward VLAN 20 traffic from the LAG to the access VLAN, and expect drops for VLAN 40/50 misses.
        3. Remove the temporary static FDB entries created for the test.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        mac7 = "00:77:77:77:77:77"
        mac8b = "00:88:88:88:88:88"
        mac9 = "00:99:99:99:99:99"

        self.npu.create_fdb(self.vlan40, mac8b, self.port26_bp)
        self.npu.create_fdb(self.vlan20, mac7, self.port26_bp)
        self.npu.create_fdb(self.vlan20, mac9, self.lag2_bp)

        try:
            pkt = simple_tcp_packet(
                eth_dst=mac7,
                eth_src=mac9,
                dl_vlan_enable=True,
                vlan_vid=20,
                ip_dst="10.0.0.1",
                ip_ttl=64,
            )
            send_packet(dataplane, 8, pkt)
            verify_packet(dataplane, pkt, 26)

            pkt = simple_tcp_packet(
                eth_dst=mac8b,
                eth_src=mac9,
                dl_vlan_enable=True,
                vlan_vid=40,
                ip_dst="10.0.0.1",
                ip_ttl=64,
            )
            send_packet(dataplane, 8, pkt)
            verify_no_other_packets(dataplane, timeout=1)

            pkt = simple_tcp_packet(
                eth_dst=mac8b,
                eth_src=mac9,
                dl_vlan_enable=True,
                vlan_vid=50,
                ip_dst="10.0.0.1",
                ip_ttl=64,
            )
            send_packet(dataplane, 7, pkt)
            verify_no_other_packets(dataplane, timeout=1)

        finally:
            self.npu.remove_fdb(self.vlan20, mac7) 
            self.npu.remove_fdb(self.vlan40, mac8b) 
            self.npu.remove_fdb(self.vlan20, mac9) 

    def _basic_vlan_flood(self, dataplane, vlan_data, pkt_u, tag_req, arp_u, arp_t):
        npu = self.npu
        for vlan_key in vlan_data.keys():
            try:
                vlan = vlan_data[vlan_key]
                tag_req[Dot1Q].vlan = vlan["vlan_id"]
                arp_t[Dot1Q].vlan = vlan["vlan_id"]
                pkt_list = [None] * vlan["large_port"]
                arp_pkt_list = [None] * vlan["large_port"]
                for port in vlan["ports"]:
                    if port not in vlan["untagged"]:
                        pkt_list[port - 1] = tag_req
                        arp_pkt_list[port - 1] = arp_t
                    else:
                        pkt_list[port - 1] = pkt_u
                        arp_pkt_list[port - 1] = arp_u
                for port in vlan["ports"]:
                    other_ports = [p for p in vlan["ports"] if p != port]
                    verify_pkt_list = [pkt_list[pl - 1] for pl in other_ports]
                    send_packet(dataplane, port, pkt_list[port - 1])
                    verify_each_packet_on_each_port(
                        dataplane,
                        verify_pkt_list,
                        other_ports,
                    )
                    time.sleep(2)
                    for send_port in other_ports:
                        send_packet(dataplane, send_port, arp_pkt_list[send_port - 1])
                        verify_packets(dataplane, arp_pkt_list[port - 1], [port])
            finally:
                _flush_dyn_fdb(npu, vlan_key)

    def test_vlan_flood(self, npu, dataplane, request):
        """
        Description:
        VLAN flooding across members with mixed tagging and dynamic FDB learning.

        Test scenario:
        1. Set native VLAN IDs on ports and LAGs, then flood/verify ARP on VLANs 40–70 with full membership.
        2. Remove four VLAN members, repeat flood with reduced port sets, then recreate members with the same tagging as setUp.
        3. Flood again with full membership; in finally restore fixture members if still removed and reset port/LAG PVIDs.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        vm44_n = vm52_n = vm63_n = vm71_n = None
        members_removed = False

        self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "40"])
        self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "50"])
        self.npu.set(self.lag10, ["SAI_LAG_ATTR_PORT_VLAN_ID", "60"])
        self.npu.set(self.lag11, ["SAI_LAG_ATTR_PORT_VLAN_ID", "70"])

        try:
            pkt_u = simple_arp_packet(
                eth_src="00:22:22:33:44:55",
                arp_op=1,
                hw_snd="00:22:22:33:44:55",
                pktlen=100,
            )
            tag_req = simple_arp_packet(
                eth_src="00:22:22:33:44:55",
                arp_op=1,
                hw_snd="00:22:22:33:44:55",
                vlan_vid=30,
                pktlen=104,
            )
            arp_u = simple_arp_packet(
                eth_dst="00:22:22:33:44:55",
                arp_op=2,
                hw_tgt="00:22:22:33:44:55",
                pktlen=100,
            )
            arp_t = simple_arp_packet(
                eth_dst="00:22:22:33:44:55",
                arp_op=2,
                hw_tgt="00:22:22:33:44:55",
                vlan_vid=30,
                pktlen=104,
            )

            vlan_ports = [26, 27, 28, 29]
            vlan_data = {
                self.vlan40: _vlan_data(40, vlan_ports, [26], 29),
                self.vlan50: _vlan_data(50, vlan_ports, [27], 29),
                self.vlan60: _vlan_data(60, vlan_ports, [28], 29),
                self.vlan70: _vlan_data(70, vlan_ports, [29], 29),
            }
            self._basic_vlan_flood(dataplane, vlan_data, pkt_u, tag_req, arp_u, arp_t)

            self.npu.remove(self.vlan_member44)
            self.npu.remove(self.vlan_member52)
            self.npu.remove(self.vlan_member63)
            self.npu.remove(self.vlan_member71)
            members_removed = True

            vlan_data = {
                self.vlan40: _vlan_data(40, [26, 27, 28], [26], 28),
                self.vlan50: _vlan_data(50, [26, 28, 29], [0], 29),
                self.vlan60: _vlan_data(60, [26, 27, 29], [0], 29),
                self.vlan70: _vlan_data(70, [27, 28, 29], [29], 29),
            }
            self._basic_vlan_flood(dataplane, vlan_data, pkt_u, tag_req, arp_u, arp_t)

            vm44_n = self.npu.create_vlan_member(
                self.vlan40, self.lag11_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )
            request.cls.vlan_member44 = vm44_n
            vm52_n = self.npu.create_vlan_member(
                self.vlan50, self.port27_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            request.cls.vlan_member52 = vm52_n
            vm63_n = self.npu.create_vlan_member(
                self.vlan60, self.lag10_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            request.cls.vlan_member63 = vm63_n
            vm71_n = self.npu.create_vlan_member(
                self.vlan70, self.port26_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )
            request.cls.vlan_member71 = vm71_n
            members_removed = False

            vlan_data = {
                self.vlan40: _vlan_data(40, vlan_ports, [26], 29),
                self.vlan50: _vlan_data(50, vlan_ports, [27], 29),
                self.vlan60: _vlan_data(60, vlan_ports, [28], 29),
                self.vlan70: _vlan_data(70, vlan_ports, [29], 29),
            }
            self._basic_vlan_flood(dataplane, vlan_data, pkt_u, tag_req, arp_u, arp_t)

        finally:
            if members_removed:
                if vm44_n is None:
                    vm44_n = self.npu.create_vlan_member(
                        self.vlan40, self.lag11_bp,
                        "SAI_VLAN_TAGGING_MODE_TAGGED",
                    )
                if vm52_n is None:
                    vm52_n = self.npu.create_vlan_member(
                        self.vlan50, self.port27_bp,
                        "SAI_VLAN_TAGGING_MODE_UNTAGGED",
                    )
                if vm63_n is None:
                    vm63_n = self.npu.create_vlan_member(
                        self.vlan60, self.lag10_bp,
                        "SAI_VLAN_TAGGING_MODE_UNTAGGED",
                    )
                if vm71_n is None:
                    vm71_n = self.npu.create_vlan_member(
                        self.vlan70, self.port26_bp,
                        "SAI_VLAN_TAGGING_MODE_TAGGED",
                    )
                request.cls.vlan_member44 = vm44_n
                request.cls.vlan_member52 = vm52_n
                request.cls.vlan_member63 = vm63_n
                request.cls.vlan_member71 = vm71_n

            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.lag10, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.lag11, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])

    def test_vlan_flood_enhanced(self, npu, dataplane):
        """
        Description:
        VLAN flooding with ports and LAGs while toggling LAG membership and extra VLAN members.

        Test scenario:
        1. Create VLANs 100/200 with members, disable learning, and align port/LAG native VLANs to 200.
        2. Add temporary LAG members on ports 24/25, verify tagged flood on VLAN 100, remove and re-add them.
        3. Remove a VLAN 100 member, verify pruning, then add VLAN 200 membership on port30 and verify flood.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        vlan100 = None
        vlan200 = None
        vm101 = vm102 = vm103 = vm104 = vm105 = None
        vm201 = vm202 = vm203 = vm204 = None
        lag_mbr32 = None
        lag_mbr42 = None
        vm205 = None
        vm105_removed = False
        port30_pvid_200 = False

        try:
            vlan100 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100"])
            vm101 = self.npu.create_vlan_member(
                vlan100, self.port26_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )
            vm102 = self.npu.create_vlan_member(
                vlan100, self.port27_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )
            vm103 = self.npu.create_vlan_member(
                vlan100, self.lag10_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )
            vm104 = self.npu.create_vlan_member(
                vlan100, self.lag11_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )
            vm105 = self.npu.create_vlan_member(
                vlan100, self.port30_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )

            vlan200 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "200"])
            vm201 = self.npu.create_vlan_member(
                vlan200, self.port26_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            vm202 = self.npu.create_vlan_member(
                vlan200, self.port27_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            vm203 = self.npu.create_vlan_member(
                vlan200, self.lag10_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            vm204 = self.npu.create_vlan_member(
                vlan200, self.lag11_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )

            self.npu.set(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
            self.npu.set(vlan200, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])
            self.npu.set(self.lag10, ["SAI_LAG_ATTR_PORT_VLAN_ID", "200"])
            self.npu.set(self.lag11, ["SAI_LAG_ATTR_PORT_VLAN_ID", "200"])

            pkt200 = simple_arp_packet(
                eth_dst="ff:ff:ff:ff:ff:ff",
                eth_src="00:22:22:33:44:55",
                arp_op=1,
                ip_tgt="10.10.10.1",
                ip_snd="10.10.10.2",
                hw_snd="00:22:22:33:44:55",
                pktlen=100,
            )
            pkt100 = simple_arp_packet(
                eth_dst="ff:ff:ff:ff:ff:ff",
                eth_src="00:22:22:33:44:55",
                arp_op=1,
                ip_tgt="10.10.10.1",
                ip_snd="10.10.10.2",
                hw_snd="00:22:22:33:44:55",
                vlan_vid=100,
                pktlen=100,
            )

            lag_mbr32 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", self.lag10, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port24])  
            lag_mbr42 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", self.lag11, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port25]) 

            lag1_ports = [28, 24]
            lag2_ports = [29, 25]
            send_packet(dataplane, 26, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [lag1_ports, lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 28, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 29, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag1_ports, [27], [30]],
            )
            send_packet(dataplane, 30, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag1_ports, lag2_ports, [27]],
            )

            self.npu.remove(lag_mbr32)
            self.npu.remove(lag_mbr42)
            lag_mbr32 = None
            lag_mbr42 = None

            lag1_ports = [28]
            lag2_ports = [29]
            send_packet(dataplane, 26, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [lag1_ports, lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 28, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 29, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag1_ports, [27], [30]],
            )
            send_packet(dataplane, 30, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag1_ports, lag2_ports, [27]],
            )

            lag_mbr32 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", self.lag10, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port24])
            lag_mbr42 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", self.lag11, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port25])

            lag1_ports = [28, 24]
            lag2_ports = [29, 25]
            send_packet(dataplane, 26, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [lag1_ports, lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 28, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 29, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag1_ports, [27], [30]],
            )
            send_packet(dataplane, 30, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 4,
                [[26], lag1_ports, lag2_ports, [27]],
            )

            self.npu.remove(vm105)
            vm105_removed = True
            send_packet(dataplane, 26, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 3,
                [lag1_ports, lag2_ports, [27]],
            )
            send_packet(dataplane, 28, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 3,
                [[26], lag2_ports, [27]],
            )
            send_packet(dataplane, 29, pkt100)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt100] * 3,
                [[26], lag1_ports, [27]],
            )

            send_packet(dataplane, 27, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 3,
                [lag1_ports, lag2_ports, [26]],
            )
            send_packet(dataplane, 24, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 3,
                [[26], lag2_ports, [27]],
            )
            send_packet(dataplane, 25, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 3,
                [[26], lag1_ports, [27]],
            )

            vm205 = self.npu.create_vlan_member(
                vlan200,
                self.port30_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            self.npu.set(self.port30, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])
            port30_pvid_200 = True
            send_packet(dataplane, 27, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 4,
                [lag1_ports, lag2_ports, [26], [30]],
            )
            send_packet(dataplane, 24, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 4,
                [[26], lag2_ports, [27], [30]],
            )
            send_packet(dataplane, 25, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 4,
                [[26], lag1_ports, [27], [30]],
            )
            send_packet(dataplane, 30, pkt200)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt200] * 4,
                [[26], lag1_ports, lag2_ports, [27]],
            )

            self.npu.remove(vm205)
            vm205 = None

        finally:
            if vm205 is not None:
                self.npu.remove(vm205)
            if port30_pvid_200:
                self.npu.set(self.port30, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            if lag_mbr32 is not None:
                self.npu.remove(lag_mbr32)
            if lag_mbr42 is not None:
                self.npu.remove(lag_mbr42)

            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.lag10, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.lag11, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])
            if vlan100 is not None:
                self.npu.set(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])
            if vlan200 is not None:
                self.npu.set(vlan200, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])

            for oid in (
                vm101,
                vm102,
                vm103,
                vm104,
                vm201,
                vm202,
                vm203,
                vm204,
            ):
                if oid is not None:
                    self.npu.remove(oid)
            if not vm105_removed and vm105 is not None:
                self.npu.remove(vm105)

            if vlan200 is not None:
                self.npu.remove(vlan200)
            if vlan100 is not None:
                self.npu.remove(vlan100)

    def test_vlan_flood_disable(self, npu, dataplane):
        """
        Description:
        Disable unknown unicast, unknown multicast, and broadcast flooding on a VLAN via SAI controls.

        Test scenario:
        1. Build VLAN 100 with four access members, disable learning, and align port native VLANs.
        2. Verify unknown unicast, multicast, and broadcast replicate to peers, then set each flood type to NONE.
        3. Confirm each traffic class is isolated after its control is disabled, then restore ports and delete VLAN 100.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        flood_none = "SAI_VLAN_FLOOD_CONTROL_TYPE_NONE"
        vlan100 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100"])
        vm101 = self.npu.create_vlan_member(vlan100, self.port24_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vm102 = self.npu.create_vlan_member(vlan100, self.port25_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vm103 = self.npu.create_vlan_member(vlan100, self.port26_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vm104 = self.npu.create_vlan_member(vlan100, self.port27_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        self.npu.set(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
        self.npu.set(self.port24, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        self.npu.set(self.port25, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])

        ucast_pkt = simple_tcp_packet(
            eth_dst=self.mac0,
            eth_src=self.mac1,
            ip_dst="10.0.0.1",
            ip_id=107,
            ip_ttl=64,
        )
        mcast_pkt = simple_tcp_packet(
            eth_dst="01:11:11:11:11:11",
            eth_src=self.mac1,
            ip_dst="231.0.0.1",
            ip_id=107,
            ip_ttl=64,
        )
        bcast_pkt = simple_tcp_packet(
            eth_dst="ff:ff:ff:ff:ff:ff",
            eth_src=self.mac1,
            ip_dst="10.0.0.1",
            ip_id=107,
            ip_ttl=64,
        )

        try:
            send_packet(dataplane, 26, ucast_pkt)
            verify_packets(dataplane, ucast_pkt, [24, 25, 27])
            send_packet(dataplane, 26, mcast_pkt)
            verify_packets(dataplane, mcast_pkt, [24, 25, 27])
            send_packet(dataplane, 26, bcast_pkt)
            verify_packets(dataplane, bcast_pkt, [24, 25, 27])

            self.npu.set(vlan100, ["SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE", flood_none])
            send_packet(dataplane, 26, ucast_pkt)
            verify_no_other_packets(dataplane, timeout=1)

            self.npu.set(vlan100, ["SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_CONTROL_TYPE", flood_none])
            send_packet(dataplane, 26, mcast_pkt)
            verify_no_other_packets(dataplane, timeout=1)

            self.npu.set(vlan100, ["SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE", flood_none])
            send_packet(dataplane, 26, bcast_pkt)
            verify_no_other_packets(dataplane, timeout=1)

        finally:
            self.npu.set(self.port24, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port25, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])
            self.npu.remove(vm101)
            self.npu.remove(vm102)
            self.npu.remove(vm103)
            self.npu.remove(vm104)
            self.npu.remove(vlan100)

    def test_vlan_stats(self, npu, dataplane):
        """
        Description:
        Verify VLAN 10 statistics match traffic-driven Python counters from earlier tests.

        Test scenario:
        1. Skip when traffic generation is disabled.
        2. Read VLAN 10 stats from the NPU and assert in/out packet and octet counters match expectations.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        stats = _vlan_stats_map(npu, self.vlan10)
        in_packets = stats["SAI_VLAN_STAT_IN_PACKETS"]
        in_ucast_packets = stats["SAI_VLAN_STAT_IN_UCAST_PKTS"]
        out_packets = stats["SAI_VLAN_STAT_OUT_PACKETS"]
        out_ucast_packets = stats["SAI_VLAN_STAT_OUT_UCAST_PKTS"]
        in_bytes = stats["SAI_VLAN_STAT_IN_OCTETS"]
        out_bytes = stats["SAI_VLAN_STAT_OUT_OCTETS"]

        assert in_packets == self.i_pkt_count
        assert in_ucast_packets == self.i_pkt_count
        assert in_bytes != 0
        assert out_packets == self.e_pkt_count
        assert out_ucast_packets == self.e_pkt_count
        assert out_bytes != 0

    def test_vlan_flood_prune(self, npu, dataplane):
        """
        Description:
        Exercise VLAN 10 ingress flood pruning with synthetic LAGs and an extra port31 path.

        Test scenario:
        1. Add a temporary LAG-based VLAN 10 member and verify flood replication to expected ports.
        2. Grow and shrink a second LAG on VLAN 10, then attach port31 via a dedicated bridge port.
        3. Restore VLAN learn mode and tear down temporary objects; always reset port31 PVID and remove the local bridge port in finally.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        self.npu.set(self.vlan10, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])

        prune_lag = self.npu.create(SaiObjType.LAG, [])
        prune_lag_mbr1 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", prune_lag, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port26])
        prune_lag_mbr2 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", prune_lag, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port27])
        prune_lag_bp = self.npu.create(SaiObjType.BRIDGE_PORT, ["SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT", 
                                                                "SAI_BRIDGE_PORT_ATTR_PORT_ID", prune_lag, "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"])
        vlan_member = self.npu.create_vlan_member(self.vlan10, prune_lag_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)
        self.npu.set(prune_lag, ["SAI_LAG_ATTR_PORT_VLAN_ID", "10"])

        prune_lag2 = None
        prune_lag2_bp = None
        vlan_member2 = None
        vlan_member3 = None
        port31_bp_local = None
        prune_lag_mbr3 = None
        prune_lag_mbr4 = None

        pkt = simple_tcp_packet(
            eth_dst="00:66:66:66:66:66",
            ip_dst="10.0.0.1",
            ip_id=107,
            ip_ttl=64,
            pktlen=96,
        )
        exp_pkt = simple_tcp_packet(
            eth_dst="00:66:66:66:66:66",
            ip_dst="10.0.0.1",
            ip_id=107,
            ip_ttl=64,
            pktlen=96,
        )
        exp_pkt_tag = simple_tcp_packet(
            eth_dst="00:66:66:66:66:66",
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_id=107,
            ip_ttl=64,
            pktlen=100,
        )

        try:
            lag0_ports = [4, 5, 6]
            lag1_ports = [26, 27]
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 3 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, [24], [1], [25]],
            )

            prune_lag2 = self.npu.create(SaiObjType.LAG, [])
            prune_lag2_bp = self.npu.create(SaiObjType.BRIDGE_PORT, ["SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT", 
                                                                     "SAI_BRIDGE_PORT_ATTR_PORT_ID", prune_lag2, "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"])
            vlan_member2 = self.npu.create_vlan_member(
                self.vlan10,
                prune_lag2_bp,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            self.npu.set(prune_lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "10"])
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 3 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, [24], [1], [25]],
            )

            prune_lag_mbr3 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", prune_lag2, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port30])
            lag2_ports = [30]
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 4 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, lag2_ports, [24], [1], [25]],
            )
            send_packet(dataplane, 30, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 4 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, [0], [24], [1], [25]],
            )

            prune_lag_mbr4 = self.npu.create(SaiObjType.LAG_MEMBER, ["SAI_LAG_MEMBER_ATTR_LAG_ID", prune_lag2, "SAI_LAG_MEMBER_ATTR_PORT_ID", self.port31])
            lag2_ports = [30, 31]
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 4 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, lag2_ports, [24], [1], [25]],
            )
            send_packet(dataplane, 31, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 4 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, [0], [24], [1], [25]],
            )

            self.npu.remove(prune_lag_mbr4)
            prune_lag_mbr4 = None
            lag2_ports = [30]
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 4 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, lag2_ports, [24], [1], [25]],
            )

            port31_bp_local = self.npu.create(SaiObjType.BRIDGE_PORT, ["SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT", 
                                                                       "SAI_BRIDGE_PORT_ATTR_PORT_ID", self.port31, "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"]) 
            vlan_member3 = self.npu.create_vlan_member(
                self.vlan10,
                port31_bp_local,
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            )
            self.npu.set(self.port31, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 5 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, lag2_ports, [24], [31], [1], [25]],
            )
            send_packet(dataplane, 31, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 5 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, lag2_ports, [0], [24], [1], [25]],
            )

            self.npu.set(self.port31, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.remove(vlan_member3)
            vlan_member3 = None
            self.npu.remove(port31_bp_local)
            port31_bp_local = None
            self.npu.remove(prune_lag_mbr3)
            prune_lag_mbr3 = None

            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [exp_pkt] * 3 + [exp_pkt_tag] * 2,
                [lag0_ports, lag1_ports, [24], [1], [25]],
            )

        finally:
            self.npu.set(self.port31, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            if vlan_member3 is not None:
                self.npu.remove(vlan_member3)
            if port31_bp_local is not None:
                self.npu.remove(port31_bp_local)

            self.npu.set(prune_lag, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])
            if prune_lag2 is not None:
                self.npu.set(prune_lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "1"])

            self.npu.remove(vlan_member)
            if vlan_member2 is not None:
                self.npu.remove(vlan_member2)

            self.npu.remove(prune_lag_mbr1)
            self.npu.remove(prune_lag_mbr2)
            if prune_lag_mbr3 is not None:
                self.npu.remove(prune_lag_mbr3)
            if prune_lag_mbr4 is not None:
                self.npu.remove(prune_lag_mbr4)

            self.npu.remove(prune_lag_bp)
            if prune_lag2_bp is not None:
                self.npu.remove(prune_lag2_bp)
            self.npu.remove(prune_lag)
            if prune_lag2 is not None:
                self.npu.remove(prune_lag2)

            self.npu.set(self.vlan10, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])

    def test_counters_clear(self, npu, dataplane):
        """
        Description:
        VLAN 10 statistics increment on forwarded traffic and clear to zero after an explicit clear_stats.

        Test scenario:
        1. Record baseline VLAN 10 stats, send a known unicast, and assert counters advance.
        2. Send a second packet to move counters again, then invoke clear_stats on VLAN 10.
        3. Read stats again and assert all monitored counters read zero.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        pkt = simple_tcp_packet(
            eth_dst=self.mac2,
            eth_src=self.mac0,
            ip_dst="172.16.0.1",
            ip_id=101,
            ip_ttl=64,
        )
        stat_keys = _vlan_stat_names()
        stats = _vlan_stats_map(self.npu, self.vlan10)
        in_bytes_pre = stats["SAI_VLAN_STAT_IN_OCTETS"]
        out_bytes_pre = stats["SAI_VLAN_STAT_OUT_OCTETS"]
        in_packets_pre = stats["SAI_VLAN_STAT_IN_PACKETS"]
        in_ucast_packets_pre = stats["SAI_VLAN_STAT_IN_UCAST_PKTS"]
        out_packets_pre = stats["SAI_VLAN_STAT_OUT_PACKETS"]
        out_ucast_packets_pre = stats["SAI_VLAN_STAT_OUT_UCAST_PKTS"]

        send_packet(dataplane, 0, pkt)
        verify_packet(dataplane, pkt, 24)

        stats = _vlan_stats_map(self.npu, self.vlan10)
        assert stats["SAI_VLAN_STAT_IN_PACKETS"] == in_packets_pre + 1
        assert stats["SAI_VLAN_STAT_IN_UCAST_PKTS"] == in_ucast_packets_pre + 1
        assert stats["SAI_VLAN_STAT_IN_OCTETS"] - in_bytes_pre != 0
        assert stats["SAI_VLAN_STAT_OUT_PACKETS"] == out_packets_pre + 1
        assert stats["SAI_VLAN_STAT_OUT_UCAST_PKTS"] == out_ucast_packets_pre + 1
        assert stats["SAI_VLAN_STAT_OUT_OCTETS"] - out_bytes_pre != 0

        send_packet(dataplane, 0, pkt)
        verify_packet(dataplane, pkt, 24)

        self.npu.clear_stats(self.vlan10, stat_keys)

        stats = _vlan_stats_map(self.npu, self.vlan10)
        assert stats["SAI_VLAN_STAT_IN_PACKETS"] == 0
        assert stats["SAI_VLAN_STAT_IN_UCAST_PKTS"] == 0
        assert stats["SAI_VLAN_STAT_IN_OCTETS"] == 0
        assert stats["SAI_VLAN_STAT_OUT_PACKETS"] == 0
        assert stats["SAI_VLAN_STAT_OUT_UCAST_PKTS"] == 0
        assert stats["SAI_VLAN_STAT_OUT_OCTETS"] == 0

    def test_vlan_member_list(self, npu):
        """
        Description:
        Validate SAI_VLAN_ATTR_MEMBER_LIST across add/remove of VLAN 10 members.

        Test scenario:
        1. Read member_list for VLAN 10; assert five members match topology OIDs vlan10_member0–4.
        2. Add vlan10_member5 (port26 untagged) and vlan10_member6 (port27 tagged); assert seven members including new OIDs.
        3. Remove the two new members and assert the list returns to five members.
        """
        expected5 = {
            self.topo.vlan10_member0,
            self.topo.vlan10_member1,
            self.topo.vlan10_member2,
            self.vlan10_member3,
            self.vlan10_member4,
        }

        status, data = npu.get(self.vlan10, ["SAI_VLAN_ATTR_MEMBER_LIST", npu.make_list(100, "oid:0x0")], False,)
        assert status == "SAI_STATUS_SUCCESS"
        vlan_members = set(data.to_list())
        assert len(vlan_members) == 5
        assert vlan_members == expected5

        vlan10_member5 = npu.create_vlan_member(self.vlan10, self.port26_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)
        vlan10_member6 = npu.create_vlan_member(self.vlan10, self.port27_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)

        expected7 = expected5 | {vlan10_member5, vlan10_member6}
        status, data = npu.get(self.vlan10, ["SAI_VLAN_ATTR_MEMBER_LIST", npu.make_list(100, "oid:0x0")], False,)
        assert status == "SAI_STATUS_SUCCESS"
        vlan_members = set(data.to_list())
        assert len(vlan_members) == 7
        assert vlan_members == expected7

        npu.remove(vlan10_member5)
        npu.remove(vlan10_member6)
        status, data = npu.get(self.vlan10, ["SAI_VLAN_ATTR_MEMBER_LIST", npu.make_list(100, "oid:0x0")], False,)
        assert status == "SAI_STATUS_SUCCESS"
        vlan_members = set(data.to_list())
        assert len(vlan_members) == 5
        assert vlan_members == expected5

    def test_vlan_negative(self, npu):
        """
        Description:
        Negative SAI validation for VLAN and VLAN_MEMBER create/get/set/remove paths.

        Test scenario:
        1. Attempt to create a duplicate VLAN ID and expect failure.
        2. Issue get/set/remove against an invalid VLAN OID and expect each operation to fail.
        3. Attempt to create a VLAN member with a logical port OID instead of a bridge port OID and expect failure.
        """
        status, vlan_dup = npu.create(
            SaiObjType.VLAN,
            ["SAI_VLAN_ATTR_VLAN_ID", "10"],
            do_assert=False,
        )

        if status == "SAI_STATUS_SUCCESS":
            npu.remove(vlan_dup)
            pytest.skip("saivs does not enforce duplicate VLAN ID uniqueness")
        assert status != "SAI_STATUS_SUCCESS"

        bad_vlan = "oid:0x1"
        try:
            status, _data = npu.get(bad_vlan, ["SAI_VLAN_ATTR_VLAN_ID", ""], False)
        except Exception:
            status = "SAI_STATUS_FAILURE"
        assert status != "SAI_STATUS_SUCCESS"

        try:
            status = npu.set(
                bad_vlan,
                ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"],
                do_assert=False,
            )
        except Exception:
            status = "SAI_STATUS_FAILURE"
        assert status != "SAI_STATUS_SUCCESS"

        try:
            status = npu.remove(bad_vlan, False)
        except Exception:
            status = "SAI_STATUS_FAILURE"
        assert status != "SAI_STATUS_SUCCESS"

        status, _ = npu.create(
            SaiObjType.VLAN_MEMBER,
            [
                "SAI_VLAN_MEMBER_ATTR_VLAN_ID", self.vlan10,
                "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", self.port0,
                "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE",
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            ],
            do_assert=False,
        )
        assert status != "SAI_STATUS_SUCCESS"

    def test_single_vlan_member(self, npu, dataplane):
        """
        Description:
        Flooding behavior on a VLAN that temporarily has only one member.

        Test scenario:
        1. Create VLAN 100 with a single tagged member on port0 and send traffic that should not replicate.
        2. Replace the member with a LAG bridge port and repeat the isolation check from the LAG side.
        3. Remove the VLAN member and VLAN object in finally.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        vlan100 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100"])
        vlan_member = self.npu.create_vlan_member(
            vlan100,
            self.port0_bp,
            "SAI_VLAN_TAGGING_MODE_TAGGED",
        )
        try:
            pkt = simple_tcp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=100,
                ip_dst="172.16.0.1",
                ip_id=102,
                ip_ttl=64,
            )
            send_packet(dataplane, 0, pkt)
            verify_no_other_packets(dataplane, timeout=1)

            self.npu.remove(vlan_member)
            vlan_member = self.npu.create_vlan_member(
                vlan100, self.lag1_bp,
                "SAI_VLAN_TAGGING_MODE_TAGGED",
            )

            pkt = simple_tcp_packet(
                eth_dst=self.mac3,
                eth_src=self.mac1,
                dl_vlan_enable=True,
                vlan_vid=100,
                ip_dst="172.16.0.1",
                ip_id=102,
                ip_ttl=64,
            )
            send_packet(dataplane, 4, pkt)
            verify_no_other_packets(dataplane, timeout=1)

        finally:
            self.npu.remove(vlan_member)
            self.npu.remove(vlan100)

    def _acl_vlan_table_attrs(self, stage):
        return [
            "SAI_ACL_TABLE_ATTR_ACL_STAGE", stage,
            "SAI_ACL_TABLE_ATTR_ACL_BIND_POINT_TYPE_LIST", "1:SAI_ACL_BIND_POINT_TYPE_VLAN",
            "SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST", "1:SAI_ACL_ACTION_TYPE_PACKET_ACTION",
            "SAI_ACL_TABLE_ATTR_FIELD_DST_IP", "true",
        ]

    def _acl_drop_entry_attrs(self, table_oid, priority):
        return [
            "SAI_ACL_ENTRY_ATTR_TABLE_ID", table_oid,
            "SAI_ACL_ENTRY_ATTR_PRIORITY", priority,
            "SAI_ACL_ENTRY_ATTR_ADMIN_STATE", "true",
            "SAI_ACL_ENTRY_ATTR_FIELD_DST_IP", "10.0.0.1&mask:255.255.255.255",
            "SAI_ACL_ENTRY_ATTR_ACTION_PACKET_ACTION", "SAI_PACKET_ACTION_DROP",
        ]

    def test_vlan_ingress_acl(self, npu, dataplane):
        """
        Description:
        Bind an ingress ACL table to VLAN 10 and verify matched traffic is dropped.

        Test scenario:
        1. Baseline-forward VLAN 10 TCP traffic toward the trunk port.
        2. Create an ACL table/entry bound to VLAN ingress that drops dst IP 10.0.0.1 and assert the binding.
        3. Resend the same traffic and expect no forwarding; remove ACL objects and clear the VLAN bind in finally.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        v10_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        exp_at_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        send_packet(dataplane, 0, v10_pkt)
        verify_packet(dataplane, exp_at_pkt, 1)

        acl_table = None
        acl_entry = None
        try:
            acl_table = self.npu.create(
                SaiObjType.ACL_TABLE,
                self._acl_vlan_table_attrs("SAI_ACL_STAGE_INGRESS"),
            )
            acl_entry = self.npu.create(
                SaiObjType.ACL_ENTRY,
                self._acl_drop_entry_attrs(acl_table, "10"),
            )
            self.npu.set(self.vlan10, ["SAI_VLAN_ATTR_INGRESS_ACL", acl_table])
            st, data = self.npu.get(self.vlan10, ["SAI_VLAN_ATTR_INGRESS_ACL", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.oid() == acl_table

            send_packet(dataplane, 0, v10_pkt)
            verify_no_other_packets(dataplane, timeout=2)

        finally:
            if acl_table is not None:
                self.npu.set(self.vlan10, ["SAI_VLAN_ATTR_INGRESS_ACL", "oid:0x0"])
            if acl_entry is not None:
                self.npu.remove(acl_entry)
            if acl_table is not None:
                self.npu.remove(acl_table)

    def test_vlan_egress_acl(self, npu, dataplane):
        """
        Description:
        Bind an egress ACL table to VLAN 10 and verify matched traffic is dropped.

        Test scenario:
        1. Baseline-forward VLAN 10 TCP traffic toward the trunk port.
        2. Create an ACL table/entry bound to VLAN egress that drops dst IP 10.0.0.1 and assert the binding.
        3. Resend the same traffic and expect no forwarding; remove ACL objects and clear the VLAN bind in finally.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        v10_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        exp_at_pkt = simple_tcp_packet(
            eth_dst=self.mac1,
            eth_src=self.mac0,
            ip_dst="10.0.0.1",
            dl_vlan_enable=True,
            vlan_vid=10,
            ip_ttl=64,
        )
        send_packet(dataplane, 0, v10_pkt)
        verify_packet(dataplane, exp_at_pkt, 1)

        acl_table = None
        acl_entry = None
        try:
            acl_table = self.npu.create(
                SaiObjType.ACL_TABLE,
                self._acl_vlan_table_attrs("SAI_ACL_STAGE_EGRESS"),
            )
            acl_entry = self.npu.create(
                SaiObjType.ACL_ENTRY,
                self._acl_drop_entry_attrs(acl_table, "10"),
            )
            self.npu.set(self.vlan10, ["SAI_VLAN_ATTR_EGRESS_ACL", acl_table])
            st, data = self.npu.get(self.vlan10, ["SAI_VLAN_ATTR_EGRESS_ACL", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.oid() == acl_table

            send_packet(dataplane, 0, v10_pkt)
            verify_no_other_packets(dataplane, timeout=2)

        finally:
            if acl_table is not None:
                self.npu.set(self.vlan10, ["SAI_VLAN_ATTR_EGRESS_ACL", "oid:0x0"])
            if acl_entry is not None:
                self.npu.remove(acl_entry)
            if acl_table is not None:
                self.npu.remove(acl_table)

    def test_vlan_learning(self, npu, dataplane):
        """
        Description:
        VLAN learn_disable at create time and runtime toggle with ARP flooding between members.

        Test scenario:
        1. Create VLANs 100/200 with learn disabled and members on ports 26/27/30.
        2. Send ARP requests and responses across VLAN 200 members and read learn_disable.
        3. Enable learning on both VLANs, re-read learn_disable, then tear down with FDB flush.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        vlan100 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100", "SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
        vm101 = self.npu.create_vlan_member(vlan100, self.port26_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)
        vm102 = self.npu.create_vlan_member(vlan100, self.port27_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)
        vm103 = self.npu.create_vlan_member(vlan100, self.port30_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)

        vlan200 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "200", "SAI_VLAN_ATTR_LEARN_DISABLE", "true"]) 
        vm201 = self.npu.create_vlan_member(vlan200, self.port26_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)
        vm202 = self.npu.create_vlan_member(vlan200, self.port27_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)
        vm203 = self.npu.create_vlan_member(vlan200, self.port30_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)

        self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])
        self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])

        pkt = simple_arp_packet(
            eth_src="00:22:22:33:44:55",
            arp_op=1,
            hw_snd="00:22:22:33:44:55",
            pktlen=100,
        )
        arp_resp = simple_arp_packet(
            eth_dst="00:22:22:33:44:55",
            arp_op=2,
            hw_tgt="00:22:22:33:44:55",
            pktlen=100,
        )

        try:
            send_packet(dataplane, 26, pkt)
            verify_packets(dataplane, pkt, [27, 30])

            send_packet(dataplane, 27, arp_resp)
            verify_packets(dataplane, arp_resp, [26, 30])

            st, data = self.npu.get(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "true"

            self.npu.set(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])
            self.npu.set(vlan200, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])

            st, data = self.npu.get(vlan100, ["SAI_VLAN_ATTR_LEARN_DISABLE", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "false"

        finally:
            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            _flush_dyn_fdb(self.npu, vlan100)
            _flush_dyn_fdb(self.npu, vlan200)
            for oid in (vm101, vm102, vm103, vm201, vm202, vm203):
                self.npu.remove(oid)
            self.npu.remove(vlan100)
            self.npu.remove(vlan200)

    def test_vlan_max_learned_addresses(self, npu, dataplane):
        """
        Description:
        Enforce max_learned_addresses on VLANs and validate static FDB installation on VLAN 200.

        Test scenario:
        1. Create VLANs 100/200 with a limit of three learned addresses and members on ports 26/27/30.
        2. Learn two dynamic entries, add a static FDB entry, then clear the max limit and verify forwarding.
        3. Flush dynamic FDB, remove the static entry by OID, restore port PVIDs, and delete VLAN objects.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        vlan100 = None
        vlan200 = None
        vm101 = vm102 = vm103 = None
        vm201 = vm202 = vm203 = None
        fdb_entry28 = None

        mac_static = "00:44:22:33:44:55"
        fdb_static_installed = False

        try:
            vlan100 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100", "SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES", "3"]) 
            vm101 = self.npu.create_vlan_member(vlan100, self.port26_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)
            vm102 = self.npu.create_vlan_member(vlan100, self.port27_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)
            vm103 = self.npu.create_vlan_member(vlan100, self.port30_bp, "SAI_VLAN_TAGGING_MODE_TAGGED",)

            vlan200 = self.npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "200", "SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES", "3"])  
            vm201 = self.npu.create_vlan_member(vlan200, self.port26_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)
            vm202 = self.npu.create_vlan_member(vlan200, self.port27_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)
            vm203 = self.npu.create_vlan_member(vlan200, self.port30_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED",)

            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "200"])

            pkt = simple_arp_packet(
                eth_src="00:22:22:33:44:55",
                arp_op=1,
                hw_snd="00:22:22:33:44:55",
                pktlen=100,
            )
            pkt_2 = simple_arp_packet(
                eth_src="00:33:22:33:44:55",
                arp_op=1,
                hw_snd="00:33:22:33:44:55",
                pktlen=100,
            )
            pkt_3 = simple_arp_packet(
                eth_src="00:44:22:33:44:55",
                arp_op=1,
                hw_snd="00:44:22:33:44:55",
                pktlen=100,
            )

            arp_resp = simple_arp_packet(
                eth_dst="00:22:22:33:44:55",
                arp_op=2,
                hw_tgt="00:22:22:33:44:55",
                pktlen=100,
            )
            arp_resp_2 = simple_arp_packet(
                eth_dst="00:33:22:33:44:55",
                arp_op=2,
                hw_tgt="00:33:22:33:44:55",
                pktlen=100,
            )
            arp_resp_3 = simple_arp_packet(
                eth_dst="00:44:22:33:44:55",
                arp_op=2,
                hw_tgt="00:44:22:33:44:55",
                pktlen=100,
            )

            send_packet(dataplane, 26, pkt)
            verify_packets(dataplane, pkt, [27, 30])

            send_packet(dataplane, 27, arp_resp)
            verify_packet(dataplane, arp_resp, 26)

            send_packet(dataplane, 26, pkt_2)
            verify_packets(dataplane, pkt_2, [27, 30])

            send_packet(dataplane, 27, arp_resp_2)
            verify_packet(dataplane, arp_resp_2, 26)

            fdb_entry28 = self.npu.create_fdb(vlan200, mac_static, self.port26_bp)

            send_packet(dataplane, 26, pkt_3)
            verify_packets(dataplane, pkt_3, [27, 30])

            send_packet(dataplane, 27, arp_resp_3)
            verify_packets(dataplane, arp_resp_3, [26, 30])

            self.npu.set(vlan100, ["SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES", "0"])
            self.npu.set(vlan200, ["SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES", "0"])

            send_packet(dataplane, 26, pkt_3)
            verify_packets(dataplane, pkt_3, [27, 30])

            send_packet(dataplane, 27, arp_resp_3)
            verify_packet(dataplane, arp_resp_3, 26)

        finally:
            _flush_dyn_fdb(self.npu, vlan100)
            _flush_dyn_fdb(self.npu, vlan200)
            if mac_static is not None:
                self.npu.remove_fdb(vlan200, mac_static)

            self.npu.set(self.port26, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            self.npu.set(self.port27, ["SAI_PORT_ATTR_PORT_VLAN_ID", "1"])
            
            for oid in (vm101, vm102, vm103, vm201, vm202, vm203):
                if oid is not None:
                    self.npu.remove(oid)
            if vlan200 is not None:
                self.npu.remove(vlan200)
            if vlan100 is not None:
                self.npu.remove(vlan100)
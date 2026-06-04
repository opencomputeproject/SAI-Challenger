import json
import time

import pytest

import saichallenger.topologies.sai_ptf_topology
from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import (
    send_packet,
    simple_arp_packet,
    simple_eth_packet,
    simple_udp_packet,
    verify_each_packet_on_multiple_port_lists,
    verify_no_other_packets,
    verify_packet_any_port,
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
    _detach_from_default(npu, list(range(len(npu.port_oids))))

    with saichallenger.topologies.sai_ptf_topology.config(npu) as topo:
        yield topo


def _detach_from_default(npu, port_indices):
    """
    Detach ports from default VLAN 1 and remove default 1Q bridge ports.
    """
    for idx in port_indices:
        bp = npu.dot1q_bp_oids[idx]
        try:
            # VLAN-member in VLAN 1
            npu.remove_vlan_member(npu.default_vlan_oid, bp)
        except Exception:
            # nothing to remove (skipped)
            pass
        try:
            # bridge-port
            npu.remove(bp)
        except Exception:
            # nothing to remove (skipped)
            pass


def _fdb_entry_key(npu, vlan_oid, mac):
    return "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
        {
            "bvid": vlan_oid,
            "mac": mac,
            "switch_id": npu.switch_oid,
        }
    )


def _sai_wait_fdb_age(timeout_sec):
    """Match sai_base_test.SaiHelper.saiWaitFdbAge (sleep timeout + 10s buffer)."""
    aging_interval_buffer = 10
    time.sleep(max(0.0, float(timeout_sec)) + aging_interval_buffer)


def _replace_tracked_oid(resource_list, old_oid, new_oid):
    """Replace a stale OID in a topology tracking list."""
    if old_oid in resource_list:
        resource_list[resource_list.index(old_oid)] = new_oid


def _refresh_topo_vlan_member(topo, member_attr, new_oid):
    """Sync topo.* attribute and def_vlan_member_list after remove+recreate."""
    _replace_tracked_oid(topo.def_vlan_member_list, getattr(topo, member_attr), new_oid)
    setattr(topo, member_attr, new_oid)


def _refresh_topo_bridge_port(topo, member_attr, new_oid):
    """Sync topo.* attribute and def_bridge_port_list after remove+recreate."""
    _replace_tracked_oid(topo.def_bridge_port_list, getattr(topo, member_attr), new_oid)
    setattr(topo, member_attr, new_oid)


def _refresh_topo_lag_member(topo, member_attr, new_oid):
    """Sync topo.* attribute and def_lag_member_list after remove+recreate."""
    _replace_tracked_oid(topo.def_lag_member_list, getattr(topo, member_attr), new_oid)
    setattr(topo, member_attr, new_oid)


class TestFdbStaticMac:
    """
    Topology for FdbStaticMacTest: provides VLAN 10, lag1, bridge ports and PVIDs.
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        request.cls.vlan_oid = topo.vlan10
        request.cls.vlan_id_int = 10
        request.cls.lag_bp_oid = topo.lag1_bp
        request.cls.dev_port0 = 0
        request.cls.dev_port1 = 1
        request.cls.lag_dev_ports = [4, 5, 6]
        request.cls.port0_bp = topo.port0_bp
        request.cls.port1_bp = topo.port1_bp
        request.cls.macs = []

        for i in range(1, 4):
            request.cls.macs.append("00:%02d:%02d:%02d:%02d:%02d" % (i, i, i, i, i))
        request.cls.dst_port_groups = [
            [request.cls.dev_port0],
            [request.cls.dev_port1],
            request.cls.lag_dev_ports,
        ]

        npu.create_fdb(request.cls.vlan_oid, request.cls.macs[0], request.cls.port0_bp)
        npu.create_fdb(request.cls.vlan_oid, request.cls.macs[1], request.cls.port1_bp)
        npu.create_fdb(request.cls.vlan_oid, request.cls.macs[2], request.cls.lag_bp_oid)

        yield
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )

    def test_fdb_static_mac_forward(self, npu, dataplane):
        """
        Description:
        Check static FDB forwarding between ports and LAG

        Test scenario:
        1. Retrieve custom VLAN, ports, and LAG from the topology fixture
        2. Create static FDB entries pointing to port 0, port 1, and LAG 1
        3. Send UDP traffic between the ports and verify forwarding to expected destinations
        4. Clean up configuration
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        for dst_ports, dst_mac in zip(self.dst_port_groups, self.macs):
            for src_port, src_mac in zip((self.dev_port0, self.dev_port1), self.macs[:1]):
                if [src_port] == dst_ports:
                    continue

                pkt = simple_udp_packet(eth_dst=dst_mac, eth_src=src_mac, pktlen=100)
                tag_pkt = simple_udp_packet(
                    eth_dst=dst_mac,
                    eth_src=src_mac,
                    dl_vlan_enable=True,
                    vlan_vid=self.vlan_id_int,
                    pktlen=104,
                )

                send_pkt = tag_pkt if src_port == self.dev_port1 else pkt
                rcv_pkt = tag_pkt if dst_ports == [self.dev_port1] else pkt

                send_packet(dataplane, src_port, send_pkt)
                verify_packet_any_port(dataplane, rcv_pkt, dst_ports)

    def test_fdb_self_forwarding_drop(self, npu, dataplane):
        """
        Description:
        Check that self-forwarding to port 0 is dropped when a static FDB entry maps the
        destination MAC to the same ingress port

        Test scenario:
        1. Retrieve VLAN and port 0 from the topology fixture
        2. Create a static FDB entry for port 0
        3. Send a UDP packet from port 0 with a destination MAC pointing to port 0
        4. Verify the self-forwarding packet is dropped
        5. Clean up configuration
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")

        pkt = simple_udp_packet(eth_dst=self.macs[0])
        send_packet(dataplane, self.dev_port0, pkt)
        verify_no_other_packets(dataplane)


class TestFdbAttribute:
    """
    Topology for FdbAttributeTest: provides VLAN 10, bridge port and test MAC address.
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        request.cls.vlan_oid = topo.vlan10
        request.cls.mac = "00:11:22:33:44:55"
        request.cls.port0_bp = topo.port0_bp

        npu.create_fdb(request.cls.vlan_oid, request.cls.mac, request.cls.port0_bp)

        yield
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )

    def test_fdb_attribute(self, npu):
        """
        Verify FDB entry attributes: bridge_port_id, type, packet_action.

        Test scenario:
        1. Get SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID and verify it matches port0_bp
        2. Get SAI_FDB_ENTRY_ATTR_TYPE and verify it is SAI_FDB_ENTRY_TYPE_STATIC
        3. Set SAI_FDB_ENTRY_ATTR_PACKET_ACTION to SAI_PACKET_ACTION_FORWARD
        4. Get SAI_FDB_ENTRY_ATTR_PACKET_ACTION and verify it is SAI_PACKET_ACTION_FORWARD
        """
        fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.mac)

        status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
        assert status == "SAI_STATUS_SUCCESS"
        assert data.oid() == self.port0_bp

        status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
        assert status == "SAI_STATUS_SUCCESS"
        assert data.value() == "SAI_FDB_ENTRY_TYPE_STATIC"

        npu.set(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
        status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
        assert status == "SAI_STATUS_SUCCESS"
        assert data.value() == "SAI_PACKET_ACTION_FORWARD"


class TestFdbNoLearn:
    """
    Topology for FdbNoLearnTest: VLAN 10 with port0/port1 and lag1.
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        request.cls._topo = topo
        request.cls.vlan_oid = topo.vlan10
        request.cls.vlan_id_int = 10
        request.cls.port0_bp = topo.port0_bp
        request.cls.port1_bp = topo.port1_bp
        request.cls.lag1_bp = topo.lag1_bp
        request.cls.vlan10_member0 = topo.vlan10_member0
        request.cls.dev_port0 = 0
        request.cls.dev_port1 = 1
        request.cls.lag_ports = [4, 5, 6]
        request.cls.port10 = topo.port10
        request.cls.src_mac = "00:11:11:11:11:11"
        request.cls.dst_mac = "00:22:22:22:22:22"

        yield
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )

    def _flood_from_port0_pkt(self):
        pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac, pktlen=100)
        tag_pkt = simple_udp_packet(
            eth_dst=self.dst_mac,
            eth_src=self.src_mac,
            dl_vlan_enable=True,
            vlan_vid=self.vlan_id_int,
            pktlen=104,
        )
        return pkt, tag_pkt

    def _reverse_pkt(self):
        pkt = simple_udp_packet(eth_dst=self.src_mac, eth_src=self.dst_mac, pktlen=100)
        tag_pkt = simple_udp_packet(
            eth_dst=self.src_mac,
            eth_src=self.dst_mac,
            dl_vlan_enable=True,
            vlan_vid=self.vlan_id_int,
            pktlen=104,
        )
        return pkt, tag_pkt

    def test_vlan_port_no_learn(self, npu, dataplane):
        """
        Description:
        Verify that MACs are not learned when VLAN learning is disabled on VLAN 10.

        Test scenario:
        1. Disable VLAN learning for VLAN 10 and send traffic from access/trunk paths.
        2. Verify flooding behavior and then restore learning mode.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt, tag_pkt = self._flood_from_port0_pkt()
        chck_pkt, tag_chck_pkt = self._reverse_pkt()
        try:
            npu.set(self.vlan_oid, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
            send_packet(dataplane, self.dev_port0, pkt)
            verify_packets(dataplane, tag_pkt, [self.dev_port1])
            verify_packet_any_port(dataplane, pkt, self.lag_ports)

            send_packet(dataplane, self.dev_port1, tag_chck_pkt)
            verify_packets(dataplane, chck_pkt, [self.dev_port0])
            verify_packet_any_port(dataplane, chck_pkt, self.lag_ports)
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            npu.set(self.vlan_oid, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])

    def test_vlan_lag_no_learn(self, npu, dataplane):
        """
        Description:
        Verify that MACs are not learned on VLAN traffic coming from LAG when VLAN learning is disabled.

        Test scenario:
        1. Disable VLAN learning on VLAN 10 and send traffic from a LAG member.
        2. Verify flooding behavior for return traffic and restore learning mode.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt, tag_pkt = self._flood_from_port0_pkt()
        chck_pkt, tag_chck_pkt = self._reverse_pkt()
        try:
            npu.set(self.vlan_oid, ["SAI_VLAN_ATTR_LEARN_DISABLE", "true"])
            send_packet(dataplane, self.lag_ports[1], pkt)
            verify_packets(dataplane, pkt, [self.dev_port0])
            verify_packets(dataplane, tag_pkt, [self.dev_port1])

            send_packet(dataplane, self.dev_port1, tag_chck_pkt)
            verify_packets(dataplane, chck_pkt, [self.dev_port0])
            verify_packet_any_port(dataplane, chck_pkt, self.lag_ports)
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            npu.set(self.vlan_oid, ["SAI_VLAN_ATTR_LEARN_DISABLE", "false"])

    def test_bp_port_no_learn(self, npu, dataplane):
        """
        Description:
        Verify that MACs are not learned when bridge-port learning is disabled on port0 bridge port.

        Test scenario:
        1. Disable FDB learning on port0 bridge port and send unknown traffic.
        2. Verify flooding behavior and restore bridge-port learning mode.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt, tag_pkt = self._flood_from_port0_pkt()
        chck_pkt, tag_chck_pkt = self._reverse_pkt()
        try:
            npu.set(self.port0_bp, ["SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE", "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE"])
            send_packet(dataplane, self.dev_port0, pkt)
            verify_packets(dataplane, tag_pkt, [self.dev_port1])
            verify_packet_any_port(dataplane, pkt, self.lag_ports)

            send_packet(dataplane, self.dev_port1, tag_chck_pkt)
            verify_packets(dataplane, chck_pkt, [self.dev_port0])
            verify_packet_any_port(dataplane, chck_pkt, self.lag_ports)
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            npu.set(self.port0_bp, ["SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE", "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW"])

    def test_bp_lag_no_learn(self, npu, dataplane):
        """
        Description:
        Verify that MACs are not learned when bridge-port learning is disabled on lag1 bridge port.

        Test scenario:
        1. Disable FDB learning on lag1 bridge port and send unknown traffic.
        2. Verify flooding behavior and restore bridge-port learning mode.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt, tag_pkt = self._flood_from_port0_pkt()
        chck_pkt, tag_chck_pkt = self._reverse_pkt()
        try:
            npu.set(self.lag1_bp, ["SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE", "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE"])
            send_packet(dataplane, self.lag_ports[1], pkt)
            verify_packets(dataplane, pkt, [self.dev_port0])
            verify_packets(dataplane, tag_pkt, [self.dev_port1])

            send_packet(dataplane, self.dev_port1, tag_chck_pkt)
            verify_packets(dataplane, chck_pkt, [self.dev_port0])
            verify_packet_any_port(dataplane, chck_pkt, self.lag_ports)
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            npu.set(self.lag1_bp, ["SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE", "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW"])

    def test_removed_bp_no_learn(self, npu, dataplane):
        """
        Description:
        Verify that MACs are not learned after removing the ingress bridge port.

        Test scenario:
        1. Remove port0 bridge port and send unknown traffic in VLAN 10.
        2. Verify flooding behavior, then recreate bridge/VLAN membership state.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt, tag_pkt = self._flood_from_port0_pkt()
        chck_pkt, tag_chck_pkt = self._reverse_pkt()
        port0_bp = self.port0_bp
        try:
            npu.remove(port0_bp)
            send_packet(dataplane, self.dev_port0, pkt)
            verify_packets(dataplane, tag_pkt, [self.dev_port1])
            verify_packet_any_port(dataplane, pkt, self.lag_ports)

            send_packet(dataplane, self.dev_port1, tag_chck_pkt)
            verify_packets(dataplane, chck_pkt, [self.dev_port0])
            verify_packet_any_port(dataplane, chck_pkt, self.lag_ports)
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            new_bp = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", npu.port_oids[self.dev_port0],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
                ],
            )
            new_member = npu.create_vlan_member(
                self.vlan_oid, new_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
            )
            topo = self._topo
            _refresh_topo_bridge_port(topo, "port0_bp", new_bp)
            self.port0_bp = new_bp
            _refresh_topo_vlan_member(topo, "vlan10_member0", new_member)
            self.vlan10_member0 = new_member

    def test_no_bp_no_learn(self, npu, dataplane):
        """
        Description:
        Verify that MACs are not learned on a port configured with PVID but without bridge-port membership.

        Test scenario:
        1. Configure PVID on physical port index 24 (no bridge port on that port).
        2. Verify flood reaches port0, port1, and LAG; verify return flood misses port24.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        if len(npu.port_oids) <= 24:
            pytest.skip("noBpNoLearnTest requires physical port index 24 (at least 25 ports)")

        pkt, tag_pkt = self._flood_from_port0_pkt()
        chck_pkt, tag_chck_pkt = self._reverse_pkt()
        try:
            npu.set(npu.port_oids[24], ["SAI_PORT_ATTR_PORT_VLAN_ID", str(self.vlan_id_int)])
            send_packet(dataplane, 24, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt, tag_pkt, pkt],
                [[self.dev_port0], [self.dev_port1], self.lag_ports],
            )
            send_packet(dataplane, self.dev_port0, chck_pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [tag_chck_pkt, chck_pkt],
                [[self.dev_port1], self.lag_ports],
            )
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            npu.set(npu.port_oids[24], ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])


class TestFdbLearn:
    """
    Topology for FdbLearnTest: VLAN 10 ports + lag1 and temporarily added lag2 (tagged).
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        request.cls._topo = topo
        request.cls.vlan_oid = topo.vlan10
        request.cls.vlan_id_int = 10
        request.cls.dev_port0 = 0
        request.cls.dev_port1 = 1
        request.cls.utg_lag_ports = [4, 5, 6]
        request.cls.tg_lag_ports = [7, 8, 9]
        request.cls.dst_port_groups = [
            [request.cls.dev_port0],
            [request.cls.dev_port1],
            request.cls.utg_lag_ports,
            request.cls.tg_lag_ports,
        ]
        request.cls.port0_bp = topo.port0_bp
        request.cls.port1_bp = topo.port1_bp
        request.cls.lag1_bp = topo.lag1_bp
        request.cls.lag2_bp = topo.lag2_bp
        request.cls.lag1 = topo.lag1
        request.cls.vlan10_member1 = topo.vlan10_member1
        request.cls.lag1_member5 = topo.lag1_member5
        request.cls.vlan10_member_lag2 = npu.create_vlan_member(
            request.cls.vlan_oid, request.cls.lag2_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
        )
        request.cls.src_ports = [
            request.cls.dev_port0,
            request.cls.dev_port1,
            4, 5, 6, 7, 8, 9,
        ]
        request.cls.macs = [
            "00:%02d:%02d:%02d:%02d:%02d" % (i, i, i, i, i) for i in range(1, len(request.cls.src_ports))
        ]
        yield
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
        )
        npu.remove(request.cls.vlan10_member_lag2)

    def test_dynamic_mac_learn(self, npu, dataplane):
        """
        Description:
        Match dynamicMacLearnTest: per-source flood lists, forwarding matrix from port0 and port1,
        optional new VLAN member on port24 and new LAG member on port25.

        Test scenario:
        1. Learning phase: flood verification per source using verify_each_packet_on_multiple_port_lists.
        2. Forwarding matrix from port0 and port1 only (PTF).
        3. Optionally add port24 to VLAN10 and port25 to LAG1 when hardware exposes enough ports.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        dst_mac = "00:11:22:33:44:55"
        try:
            # learning phase — full per-source flood packet-list verification
            for src_port, src_mac in zip(self.src_ports, self.macs):
                pkt = simple_udp_packet(eth_dst=dst_mac, eth_src=src_mac, pktlen=100)
                tag_pkt = simple_udp_packet(
                    eth_dst=dst_mac,
                    eth_src=src_mac,
                    dl_vlan_enable=True,
                    vlan_vid=self.vlan_id_int,
                    pktlen=104,
                )
                send_pkt = tag_pkt if src_port in (self.dev_port1, *self.tg_lag_ports) else pkt
                flood_port_list = [
                    self.dst_port_groups[p]
                    for p in range(len(self.dst_port_groups))
                    if src_port not in self.dst_port_groups[p]
                ]
                flood_pkt_list = []
                tg_lag_set = False
                utg_lag_set = False
                for dst_group in self.dst_port_groups:
                    if src_port in dst_group:
                        continue
                    if dst_group == [self.dev_port0]:
                        flood_pkt_list.append(pkt)
                    elif dst_group == [self.dev_port1]:
                        flood_pkt_list.append(tag_pkt)
                    elif dst_group == self.utg_lag_ports and not utg_lag_set:
                        flood_pkt_list.append(pkt)
                        utg_lag_set = True
                    elif dst_group == self.tg_lag_ports and not tg_lag_set:
                        flood_pkt_list.append(tag_pkt)
                        tg_lag_set = True
                send_packet(dataplane, src_port, send_pkt)
                verify_each_packet_on_multiple_port_lists(dataplane, flood_pkt_list, flood_port_list)

            # verification phase — nested forwarding from both source paths (port0 and port1)
            for dst_port, dst_mac_l in zip(self.src_ports, self.macs):
                for src_port, src_mac in zip((self.dev_port0, self.dev_port1), (self.macs[0], self.macs[1])):
                    if src_port == dst_port:
                        continue
                    pkt = simple_udp_packet(eth_dst=dst_mac_l, eth_src=src_mac, pktlen=100)
                    tag_pkt = simple_udp_packet(
                        eth_dst=dst_mac_l,
                        eth_src=src_mac,
                        dl_vlan_enable=True,
                        vlan_vid=self.vlan_id_int,
                        pktlen=104,
                    )
                    send_pkt = tag_pkt if src_port in (self.dev_port1, *self.tg_lag_ports) else pkt
                    rcv_pkt = tag_pkt if dst_port in (self.dev_port1, *self.tg_lag_ports) else pkt
                    if dst_port in self.utg_lag_ports:
                        rcv_port = self.utg_lag_ports
                    elif dst_port in self.tg_lag_ports:
                        rcv_port = self.tg_lag_ports
                    else:
                        rcv_port = [dst_port]
                    send_packet(dataplane, src_port, send_pkt)
                    verify_packet_any_port(dataplane, rcv_pkt, rcv_port)

            new_vlan_member_oid = None
            new_vlan_bp = None
            port24_oid = None
            lag1_member25 = None
            if len(npu.port_oids) > 24:
                port24_oid = npu.port_oids[24]
                new_vlan_bp = npu.create(
                    SaiObjType.BRIDGE_PORT,
                    [
                        "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                        "SAI_BRIDGE_PORT_ATTR_PORT_ID", port24_oid,
                        "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
                    ],
                )
                new_vlan_member_oid = npu.create_vlan_member(
                    self.vlan_oid, new_vlan_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
                )
                npu.set(port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", str(self.vlan_id_int)])
                new_vlan_member_mac = "00:12:34:56:78:90"
                pkt_nv = simple_udp_packet(eth_dst=new_vlan_member_mac, eth_src=self.macs[0], pktlen=100)
                tag_nv = simple_udp_packet(
                    eth_dst=new_vlan_member_mac,
                    eth_src=self.macs[0],
                    dl_vlan_enable=True,
                    vlan_vid=self.vlan_id_int,
                    pktlen=104,
                )
                send_packet(dataplane, self.dev_port0, pkt_nv)
                verify_each_packet_on_multiple_port_lists(
                    dataplane,
                    [tag_nv, pkt_nv, tag_nv, pkt_nv],
                    [[self.dev_port1], self.utg_lag_ports, self.tg_lag_ports, [24]],
                )
                pkt_f = simple_udp_packet(eth_dst=dst_mac, eth_src=new_vlan_member_mac, pktlen=100)
                tag_f = simple_udp_packet(
                    eth_dst=dst_mac,
                    eth_src=new_vlan_member_mac,
                    dl_vlan_enable=True,
                    vlan_vid=self.vlan_id_int,
                    pktlen=104,
                )
                send_packet(dataplane, 24, pkt_f)
                verify_each_packet_on_multiple_port_lists(
                    dataplane,
                    [pkt_f, tag_f, pkt_f, tag_f],
                    self.dst_port_groups,
                )
                time.sleep(2)
                pkt_chk = simple_udp_packet(eth_dst=new_vlan_member_mac, eth_src=self.macs[0], pktlen=100)
                send_packet(dataplane, self.dev_port0, pkt_chk)
                verify_packets(dataplane, pkt_chk, [24])

            utg_for_lag = list(self.utg_lag_ports)
            if len(npu.port_oids) > 25:
                if new_vlan_member_oid is None:
                    pytest.skip("new VLAN member block requires port24; topology has port25 but not port24")
                port25_oid = npu.port_oids[25]
                new_lag_mac = "00:09:87:65:43:21"
                lag1_member25 = npu.create(
                    SaiObjType.LAG_MEMBER,
                    [
                        "SAI_LAG_MEMBER_ATTR_LAG_ID", self.lag1,
                        "SAI_LAG_MEMBER_ATTR_PORT_ID", port25_oid,
                    ],
                )
                utg_for_lag.append(25)
                pkt_l = simple_udp_packet(eth_dst=dst_mac, eth_src=new_lag_mac, pktlen=100)
                tag_l = simple_udp_packet(
                    eth_dst=dst_mac,
                    eth_src=new_lag_mac,
                    dl_vlan_enable=True,
                    vlan_vid=self.vlan_id_int,
                    pktlen=104,
                )
                send_packet(dataplane, 25, pkt_l)
                verify_each_packet_on_multiple_port_lists(
                    dataplane,
                    [pkt_l, tag_l, tag_l, pkt_l],
                    [
                        [self.dev_port0], [self.dev_port1],
                        self.tg_lag_ports, [24],
                    ],
                )
                time.sleep(2)
                pkt_tl = simple_udp_packet(eth_dst=new_lag_mac, eth_src=self.macs[0], pktlen=100)
                send_packet(dataplane, self.dev_port0, pkt_tl)
                verify_packet_any_port(dataplane, pkt_tl, utg_for_lag)

        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )
            if lag1_member25 is not None:
                npu.remove(lag1_member25)
            if port24_oid is not None:
                npu.set(port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
            if new_vlan_member_oid is not None:
                npu.remove(new_vlan_member_oid)
            if new_vlan_bp is not None:
                npu.remove(new_vlan_bp)

    def test_mac_learn_error(self, npu, dataplane):
        """
        Description:
        Match macLearnErrorTest cases 1–6 (invalid tag, bcast/mcast src, static src, removed VLAN/LAG member).

        Test scenario:
        1. Install static FDB for access and trunk ports; run six negative/flood cases; restore topology.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        access_port = self.dev_port0
        trunk_port = self.dev_port1
        ap_mac = self.macs[0]
        tp_mac = self.macs[1]
        flood_port_list = [[trunk_port], self.utg_lag_ports, self.tg_lag_ports]

        npu.create_fdb(self.vlan_oid, ap_mac, self.port0_bp)
        npu.create_fdb(self.vlan_oid, tp_mac, self.port1_bp)
        vlan_removed = False
        lag_removed = False
        try:
            # Case 1 — invalid VLAN tag
            lrn_mac = self.macs[2]
            inv_vlan_tag_pkt = simple_udp_packet(
                eth_dst=ap_mac, eth_src=lrn_mac, dl_vlan_enable=True, vlan_vid=100, pktlen=104
            )
            chck_inv_vlan_pkt = simple_udp_packet(eth_dst=lrn_mac, eth_src=ap_mac, pktlen=100)
            chck_inv_vlan_tag_pkt = simple_udp_packet(
                eth_dst=lrn_mac, eth_src=ap_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, trunk_port, inv_vlan_tag_pkt)
            verify_no_other_packets(dataplane)
            send_packet(dataplane, access_port, chck_inv_vlan_pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [chck_inv_vlan_tag_pkt, chck_inv_vlan_pkt, chck_inv_vlan_tag_pkt],
                flood_port_list,
            )

            # Case 2 — broadcast src
            bcast_mac = "ff:ff:ff:ff:ff:ff"
            bcast_src_tag_pkt = simple_udp_packet(
                eth_dst=ap_mac, eth_src=bcast_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            chck_bcast_src_pkt = simple_udp_packet(eth_dst=bcast_mac, eth_src=ap_mac, pktlen=100)
            chck_bcast_src_tag_pkt = simple_udp_packet(
                eth_dst=bcast_mac, eth_src=ap_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, trunk_port, bcast_src_tag_pkt)
            verify_no_other_packets(dataplane)
            send_packet(dataplane, access_port, chck_bcast_src_pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [chck_bcast_src_tag_pkt, chck_bcast_src_pkt, chck_bcast_src_tag_pkt],
                flood_port_list,
            )

            # Case 3 — multicast src
            mcast_mac = "01:00:5e:11:22:33"
            mcast_src_tag_pkt = simple_udp_packet(
                eth_dst=ap_mac, eth_src=mcast_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            chck_mcast_src_pkt = simple_udp_packet(eth_dst=mcast_mac, eth_src=ap_mac, pktlen=100)
            chck_mcast_src_tag_pkt = simple_udp_packet(
                eth_dst=mcast_mac, eth_src=ap_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, trunk_port, mcast_src_tag_pkt)
            verify_no_other_packets(dataplane)
            send_packet(dataplane, access_port, chck_mcast_src_pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [chck_mcast_src_tag_pkt, chck_mcast_src_pkt, chck_mcast_src_tag_pkt],
                flood_port_list,
            )

            # Case 4 — src_mac statically added (ap_mac); learning conflict with lrn_mac on LAG
            lrn_mac = self.macs[2]
            bcast_dst = "ff:ff:ff:ff:ff:ff"
            static_src_tag_pkt = simple_udp_packet(
                eth_dst=bcast_dst, eth_src=ap_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            static_src_pkt = simple_udp_packet(eth_dst=bcast_dst, eth_src=ap_mac, pktlen=100)
            chck_static_src_pkt = simple_udp_packet(eth_dst=ap_mac, eth_src=lrn_mac, pktlen=100)
            send_packet(dataplane, trunk_port, static_src_tag_pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [static_src_pkt, static_src_pkt, static_src_tag_pkt],
                [[access_port], self.utg_lag_ports, self.tg_lag_ports],
            )
            send_packet(dataplane, self.utg_lag_ports[1], chck_static_src_pkt)
            verify_packets(dataplane, chck_static_src_pkt, [access_port])

            # Case 5 — removed VLAN member (port1 from VLAN10)
            rm_vlan_member = self.vlan10_member1
            rm_vlan_member_dev = self.dev_port1
            rm_vlan_member_mac = "00:12:34:56:78:90"
            npu.remove(rm_vlan_member)
            vlan_removed = True
            pkt = simple_udp_packet(eth_dst=bcast_dst, eth_src=self.macs[0], pktlen=100)
            tag_pkt = simple_udp_packet(
                eth_dst=bcast_dst,
                eth_src=self.macs[0],
                dl_vlan_enable=True,
                vlan_vid=self.vlan_id_int,
                pktlen=104,
            )
            flood_port_list5 = [self.utg_lag_ports, self.tg_lag_ports]
            send_packet(dataplane, self.dev_port0, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [pkt, tag_pkt], flood_port_list5)
            tag_rm = simple_udp_packet(
                eth_dst=bcast_dst,
                eth_src=rm_vlan_member_mac,
                dl_vlan_enable=True,
                vlan_vid=self.vlan_id_int,
                pktlen=104,
            )
            send_packet(dataplane, rm_vlan_member_dev, tag_rm)
            verify_no_other_packets(dataplane)
            pkt_nv = simple_udp_packet(eth_dst=rm_vlan_member_mac, eth_src=self.macs[0], pktlen=100)
            tag_nv = simple_udp_packet(
                eth_dst=rm_vlan_member_mac,
                eth_src=self.macs[0],
                dl_vlan_enable=True,
                vlan_vid=self.vlan_id_int,
                pktlen=104,
            )
            send_packet(dataplane, self.dev_port0, pkt_nv)
            verify_each_packet_on_multiple_port_lists(dataplane, [pkt_nv, tag_nv], flood_port_list5)

            # Case 6 — removed LAG member (port5)
            rm_lag_member = self.lag1_member5
            rm_lag_member_dev = 5
            rm_lag_member_mac = "00:09:87:65:43:21"
            npu.remove(rm_lag_member)
            lag_removed = True
            utg_rm = [p for p in self.utg_lag_ports if p != rm_lag_member_dev]
            pkt_l = simple_udp_packet(eth_dst=bcast_dst, eth_src=rm_lag_member_mac, pktlen=100)
            send_packet(dataplane, rm_lag_member_dev, pkt_l)
            verify_no_other_packets(dataplane)
            pkt_chk = simple_udp_packet(eth_dst=rm_lag_member_mac, eth_src=self.macs[0], pktlen=100)
            tag_chk = simple_udp_packet(
                eth_dst=rm_lag_member_mac,
                eth_src=self.macs[0],
                dl_vlan_enable=True,
                vlan_vid=self.vlan_id_int,
                pktlen=104,
            )
            send_packet(dataplane, self.dev_port0, pkt_chk)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt_chk, tag_chk],
                [[trunk_port], utg_rm, self.tg_lag_ports],
            )

        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )
            topo = self._topo
            if lag_removed:
                new_lm = npu.create(
                    SaiObjType.LAG_MEMBER,
                    [
                        "SAI_LAG_MEMBER_ATTR_LAG_ID", self.lag1,
                        "SAI_LAG_MEMBER_ATTR_PORT_ID", npu.port_oids[5],
                    ],
                )
                _refresh_topo_lag_member(topo, "lag1_member5", new_lm)
                self.lag1_member5 = new_lm
            if vlan_removed:
                new_vm = npu.create_vlan_member(self.vlan_oid, self.port1_bp, "SAI_VLAN_TAGGING_MODE_TAGGED")
                _refresh_topo_vlan_member(topo, "vlan10_member1", new_vm)
                self.vlan10_member1 = new_vm


class TestFdbMacMove:
    """
    Topology for FdbMacMoveTest: VLAN 10 with port1 untagged, extra access port24,
    static chck_mac on port24_bp, and lag10 (ports 25–27) in VLAN 10.
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        if len(npu.port_oids) < 28:
            pytest.skip("FdbMacMoveTest requires physical port indices 0–27 (28 ports)")
        request.cls.vlan_oid = topo.vlan10
        request.cls.port0_bp = topo.port0_bp
        request.cls.port1_bp = topo.port1_bp
        request.cls.lag1_bp = topo.lag1_bp
        request.cls.port0 = topo.port0
        request.cls.port1 = topo.port1
        request.cls.lag1 = topo.lag1
        request.cls.dev_port0 = 0
        request.cls.dev_port1 = 1
        request.cls.dev_port5 = 5
        request.cls.dev_port24 = 24
        request.cls.dev_port27 = 27
        request.cls.lag1_ports = [4, 5, 6]
        request.cls.lag3_ports = [25, 26, 27]
        request.cls.moving_mac = "00:11:22:33:44:55"
        request.cls.chck_mac = "00:11:11:11:11:11"

        old_vlan10_member1 = topo.vlan10_member1
        npu.remove(old_vlan10_member1)
        vlan10_member1_ut = npu.create_vlan_member(
            request.cls.vlan_oid, topo.port1_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
        )
        npu.set(topo.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])

        port24_oid = npu.port_oids[24]
        port24_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", port24_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        vlan10_member3 = npu.create_vlan_member(
            request.cls.vlan_oid, port24_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
        )
        npu.set(port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])

        lag10 = npu.create(SaiObjType.LAG, [])
        lag10_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", lag10,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        lag10_members = []
        for pidx in (25, 26, 27):
            lag10_members.append(
                npu.create(
                    SaiObjType.LAG_MEMBER,
                    [
                        "SAI_LAG_MEMBER_ATTR_LAG_ID", lag10,
                        "SAI_LAG_MEMBER_ATTR_PORT_ID", npu.port_oids[pidx],
                    ],
                )
            )
        vlan10_member4 = npu.create_vlan_member(
            request.cls.vlan_oid, lag10_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
        )
        npu.set(lag10, ["SAI_LAG_ATTR_PORT_VLAN_ID", "10"])

        request.cls.lag10_bp = lag10_bp
        request.cls.port24_bp = port24_bp
        npu.create_fdb(request.cls.vlan_oid, request.cls.chck_mac, port24_bp)

        request.cls._topo = topo
        request.cls._vlan10_member1_ut = vlan10_member1_ut
        request.cls._port24_oid = port24_oid
        request.cls._vlan10_member3 = vlan10_member3
        request.cls._lag10 = lag10
        request.cls._lag10_bp = lag10_bp
        request.cls._lag10_members = lag10_members
        request.cls._vlan10_member4 = vlan10_member4

        yield

        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
        )
        npu.set(topo.lag1, ["SAI_LAG_ATTR_PORT_VLAN_ID", "0"])
        npu.remove(request.cls._vlan10_member4)
        for lm in reversed(request.cls._lag10_members):
            npu.remove(lm)
        npu.remove(request.cls._lag10_bp)
        npu.remove(request.cls._lag10)
        npu.set(request.cls._port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.remove(request.cls._vlan10_member3)
        npu.remove(request.cls.port24_bp)
        npu.set(topo.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.remove(request.cls._vlan10_member1_ut)
        new_member = npu.create_vlan_member(
            request.cls.vlan_oid, topo.port1_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
        )
        _refresh_topo_vlan_member(topo, "vlan10_member1", new_member)

    def test_dynamic_mac_move(self, npu, dataplane):
        """
        Description:
        Verify dynamic MAC moves along port→port→LAG1→LAG3→port1 with verification on port24.

        Test scenario:
        1. For each ingress in the move chain, learn toward chck_mac and verify return path.
        2. Flush dynamic FDB entries (static chck_mac on port24 remains).
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt = simple_udp_packet(eth_dst=self.chck_mac, eth_src=self.moving_mac)
        chck_pkt = simple_udp_packet(eth_dst=self.moving_mac, eth_src=self.chck_mac)
        port_chain = [self.dev_port0, self.dev_port1, self.dev_port5, self.dev_port27, self.dev_port1]
        chck_port = self.dev_port24
        try:
            for src_port in port_chain:
                send_packet(dataplane, src_port, pkt)
                verify_packets(dataplane, pkt, [chck_port])
                send_packet(dataplane, chck_port, chck_pkt)
                if src_port in self.lag1_ports:
                    verify_packet_any_port(dataplane, chck_pkt, self.lag1_ports)
                elif src_port in self.lag3_ports:
                    verify_packet_any_port(dataplane, chck_pkt, self.lag3_ports)
                else:
                    verify_packets(dataplane, chck_pkt, [src_port])
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
            )

    def test_dynamic_mac_move_static_entry(self, npu, dataplane):
        """
        Description:
        Same move chain as dynamic MAC move with moving MAC installed as static with allow_mac_move.

        Test scenario:
        1. Create static FDB for moving_mac on port0 with allow_mac_move true.
        2. Run the same ingress chain and verification as dynamicMacMoveTest(static_entry=True).
        3. Remove the moving static FDB entry in teardown of the test body.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        moving_key = _fdb_entry_key(npu, self.vlan_oid, self.moving_mac)
        pkt = simple_udp_packet(eth_dst=self.chck_mac, eth_src=self.moving_mac)
        chck_pkt = simple_udp_packet(eth_dst=self.moving_mac, eth_src=self.chck_mac)
        port_chain = [self.dev_port0, self.dev_port1, self.dev_port5, self.dev_port27, self.dev_port1]
        chck_port = self.dev_port24
        try:
            npu.create(
                moving_key,
                [
                    "SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_STATIC",
                    "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", self.port0_bp,
                    "SAI_FDB_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD",
                    "SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE", "true",
                ],
            )
            for src_port in port_chain:
                send_packet(dataplane, src_port, pkt)
                verify_packets(dataplane, pkt, [chck_port])
                send_packet(dataplane, chck_port, chck_pkt)
                if src_port in self.lag1_ports:
                    verify_packet_any_port(dataplane, chck_pkt, self.lag1_ports)
                elif src_port in self.lag3_ports:
                    verify_packet_any_port(dataplane, chck_pkt, self.lag3_ports)
                else:
                    verify_packets(dataplane, chck_pkt, [src_port])
        finally:
            npu.remove(moving_key)

    def test_static_mac_move(self, npu, dataplane):
        """
        Description:
        Verify static MAC forwarding after programmatic bridge-port updates (staticMacMoveTest).

        Test scenario:
        1. Create static FDB for moving_mac on port0; iterate port/bp chain matching PTF.
        2. Send from port24 and verify delivery on port, LAG1, or LAG3 as programmed.
        3. Remove the moving static FDB entry when done.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.moving_mac)
        port_chain = [self.dev_port0, self.dev_port1, self.dev_port5, self.dev_port27, self.dev_port1]
        bport_chain = [self.port0_bp, self.port1_bp, self.lag1_bp, self.lag10_bp, self.port1_bp]
        chck_pkt = simple_udp_packet(eth_dst=self.moving_mac, eth_src=self.chck_mac)
        try:
            npu.create_fdb(self.vlan_oid, self.moving_mac, self.port0_bp, entry_type="SAI_FDB_ENTRY_TYPE_STATIC")
            for port, bport in zip(port_chain, bport_chain):
                npu.set(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bport])
                send_packet(dataplane, self.dev_port24, chck_pkt)
                if port in self.lag1_ports:
                    verify_packet_any_port(dataplane, chck_pkt, self.lag1_ports)
                elif port in self.lag3_ports:
                    verify_packet_any_port(dataplane, chck_pkt, self.lag3_ports)
                else:
                    verify_packets(dataplane, chck_pkt, [port])
        finally:
            npu.remove(fdb_key)


class TestFdbFlush:
    """
    Topology for FdbFlushTest: port1/port3/lag2 retagged like PTF, trunk stub on port24, dual flood+forward checks.
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        if len(npu.port_oids) <= 24:
            pytest.skip("FdbFlushTest requires physical port index 24 (25 ports)")

        vlan10_oid = None
        vlan20_oid = None
        port24_bp = None
        vlan10_member1_ut = None
        vlan20_member1_ut = None
        vlan20_member2_ut = None

        try:
            _m = npu.get_vlan_member(topo.vlan10, topo.port1_bp)
            if _m is not None:
                npu.remove(_m)
            vlan10_member1_ut = npu.create_vlan_member(
                topo.vlan10, topo.port1_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
            )
            npu.set(topo.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])

            _m = npu.get_vlan_member(topo.vlan20, topo.port3_bp)
            if _m is not None:
                npu.remove(_m)
            vlan20_member1_ut = npu.create_vlan_member(
                topo.vlan20, topo.port3_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
            )
            npu.set(topo.port3, ["SAI_PORT_ATTR_PORT_VLAN_ID", "20"])

            _m = npu.get_vlan_member(topo.vlan20, topo.lag2_bp)
            if _m is not None:
                npu.remove(_m)
            vlan20_member2_ut = npu.create_vlan_member(
                topo.vlan20, topo.lag2_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
            )
            npu.set(topo.lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "20"])

            port24_bp = npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", npu.port_oids[24],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
                ],
            )

            vlan10_oid = topo.vlan10
            vlan20_oid = topo.vlan20

            request.cls.vlan10 = vlan10_oid
            request.cls.vlan20 = vlan20_oid
            request.cls.vlan10_id = 10
            request.cls.vlan20_id = 20
            request.cls.port1 = topo.port1
            request.cls.port3 = topo.port3
            request.cls.lag2 = topo.lag2
            request.cls.port24_bp = port24_bp
            request.cls.trunk_port_bp = port24_bp
            request.cls.trunk_dev_port = 24

            request.cls.dev_port0 = 0
            request.cls.dev_port1 = 1
            request.cls.dev_port2 = 2
            request.cls.dev_port3 = 3
            request.cls.vlan10_ports = [0, 1, 4, 5, 6]
            request.cls.vlan10_bps = [topo.port0_bp, topo.port1_bp, topo.lag1_bp, topo.lag1_bp, topo.lag1_bp]
            request.cls.vlan10_lag_ports = [4, 5, 6]
            request.cls.vlan20_ports = [2, 3, 7, 8, 9]
            request.cls.vlan20_bps = [topo.port2_bp, topo.port3_bp, topo.lag2_bp, topo.lag2_bp, topo.lag2_bp]
            request.cls.vlan20_lag_ports = [7, 8, 9]
            request.cls.vlan10_stat_macs = ["00:10:00:%02d:%02d:%02d" % (i, i, i) for i in range(1, 6)]
            request.cls.vlan10_dyn_macs = ["00:10:ff:%02d:%02d:%02d" % (i, i, i) for i in range(1, 6)]
            request.cls.vlan20_stat_macs = ["00:20:00:%02d:%02d:%02d" % (i, i, i) for i in range(1, 6)]
            request.cls.vlan20_dyn_macs = ["00:20:ff:%02d:%02d:%02d" % (i, i, i) for i in range(1, 6)]

            request.cls.tp10_stat_mac = "00:10:00:66:66:66"
            request.cls.tp10_dyn_mac = "00:10:ff:66:66:66"
            request.cls.tp20_stat_mac = "00:20:00:66:66:66"
            request.cls.tp20_dyn_mac = "00:20:ff:66:66:66"
            request.cls.vlan10_member3 = None
            request.cls.vlan20_member3 = None

            request.cls._vlan10_member1_ut = vlan10_member1_ut
            request.cls._vlan20_member1_ut = vlan20_member1_ut
            request.cls._vlan20_member2_ut = vlan20_member2_ut

            yield
        finally:
            # SAI-oriented teardown: flush FDB → remove VLAN members (incl. test trunk) →
            # remove objects we created (bridge port). Topology VLANs/LAGs are not removed here.
            _cli = getattr(npu, "sai_client", None)
            _sw = npu.switch_oid
            _switch_vid_ok = (
                _cli is None
                or not isinstance(_sw, str)
                or not _sw.startswith("oid:")
                or not hasattr(_cli, "vid_to_rid")
                or _cli.vid_to_rid(_sw) is not None
            )
            if vlan10_oid is not None and vlan20_oid is not None and _switch_vid_ok:
                npu.flush_fdb_entries(
                    npu.switch_oid, ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"]
                )

            for _mbr_attr in ("vlan10_member3", "vlan20_member3"):
                _mbr = getattr(request.cls, _mbr_attr, None)
                if _mbr is not None:
                    npu.remove(_mbr)
                    setattr(request.cls, _mbr_attr, None)

            if port24_bp is not None:
                npu.remove(port24_bp)

            if vlan10_member1_ut is not None:
                npu.set(topo.port1, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
                npu.remove(vlan10_member1_ut)
                new_member = npu.create_vlan_member(
                    topo.vlan10, topo.port1_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
                )
                _refresh_topo_vlan_member(topo, "vlan10_member1", new_member)

            if vlan20_member1_ut is not None:
                npu.set(topo.port3, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
                npu.remove(vlan20_member1_ut)
                new_member = npu.create_vlan_member(
                    topo.vlan20, topo.port3_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
                )
                _refresh_topo_vlan_member(topo, "vlan20_member1", new_member)

            if vlan20_member2_ut is not None:
                npu.set(topo.lag2, ["SAI_LAG_ATTR_PORT_VLAN_ID", "0"])
                npu.remove(vlan20_member2_ut)
                new_member = npu.create_vlan_member(
                    topo.vlan20, topo.lag2_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
                )
                _refresh_topo_vlan_member(topo, "vlan20_member2", new_member)

    def _prepare_fdb(self, npu, dataplane):
        npu.flush_fdb_entries(npu.switch_oid, ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])
        for mac, bp in zip(self.vlan10_stat_macs, self.vlan10_bps):
            npu.create_fdb(self.vlan10, mac, bp, entry_type="SAI_FDB_ENTRY_TYPE_STATIC")
        for mac, bp in zip(self.vlan20_stat_macs, self.vlan20_bps):
            npu.create_fdb(self.vlan20, mac, bp, entry_type="SAI_FDB_ENTRY_TYPE_STATIC")

        for mac, port in zip(self.vlan10_dyn_macs, self.vlan10_ports):
            send_packet(dataplane, port, simple_udp_packet(eth_dst="ff:ff:ff:ff:ff:ff", eth_src=mac))
        for mac, port in zip(self.vlan20_dyn_macs, self.vlan20_ports):
            send_packet(dataplane, port, simple_udp_packet(eth_dst="ff:ff:ff:ff:ff:ff", eth_src=mac))
        time.sleep(2)
        dataplane.flush()

    def _verify_fwd(self, dataplane, dst_macs, dst_ports, src_macs, src_ports, lag_ports,
                    trunk_port=None, vlan_id=None):
        for dst_mac, dst_port in zip(dst_macs, dst_ports):
            for src_mac, src_port in zip(src_macs, src_ports):
                if src_port == dst_port:
                    continue
                pkt = simple_udp_packet(eth_dst=dst_mac, eth_src=src_mac, pktlen=100)
                rcv_pkt = pkt
                if trunk_port is not None and dst_port == trunk_port:
                    rcv_pkt = simple_udp_packet(
                        eth_dst=dst_mac,
                        eth_src=src_mac,
                        dl_vlan_enable=True,
                        vlan_vid=vlan_id,
                        pktlen=104,
                    )
                rcv_port = lag_ports if dst_port in lag_ports else [dst_port]
                send_packet(dataplane, src_port, pkt)
                verify_packet_any_port(dataplane, rcv_pkt, rcv_port)
                break

    def _verify_flood(self, dataplane, dst_macs, dst_ports, src_macs, src_ports, lag_ports,
                      trunk_port=None, vlan_id=None):
        for dst_mac in dst_macs:
            for src_mac, src_port in zip(src_macs, src_ports):
                if src_mac == dst_mac:
                    continue
                pkt = simple_udp_packet(eth_dst=dst_mac, eth_src=src_mac, pktlen=100)
                port_list = []
                lag_set = False
                for port in dst_ports:
                    if port == src_port:
                        continue
                    if port in lag_ports:
                        if lag_set:
                            continue
                        port_list.append(lag_ports)
                        lag_set = True
                    else:
                        port_list.append([port])
                pkt_list = [pkt] * len(port_list)
                if trunk_port is not None:
                    port_list.append([trunk_port])
                    tag_pkt = simple_udp_packet(
                        eth_dst=dst_mac,
                        eth_src=src_mac,
                        dl_vlan_enable=True,
                        vlan_vid=vlan_id,
                        pktlen=104,
                    )
                    pkt_list.append(tag_pkt)
                send_packet(dataplane, src_port, pkt)
                verify_each_packet_on_multiple_port_lists(dataplane, pkt_list, port_list)
                break

    def _set_up_trunk_port(self, npu, dataplane):
        self.tp10_stat_mac = "00:10:00:66:66:66"
        self.tp10_dyn_mac = "00:10:ff:66:66:66"
        chck_vlan10_mac = self.vlan10_stat_macs[0]
        self.tp20_stat_mac = "00:20:00:66:66:66"
        self.tp20_dyn_mac = "00:20:ff:66:66:66"
        chck_vlan20_mac = self.vlan20_stat_macs[0]

        self.vlan10_member3 = npu.create_vlan_member(
            self.vlan10, self.trunk_port_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
        )
        self.vlan20_member3 = npu.create_vlan_member(
            self.vlan20, self.trunk_port_bp, "SAI_VLAN_TAGGING_MODE_TAGGED"
        )

        npu.create_fdb(self.vlan10, self.tp10_stat_mac, self.trunk_port_bp)
        npu.create_fdb(self.vlan20, self.tp20_stat_mac, self.trunk_port_bp)

        tag_vlan10_pkt = simple_udp_packet(
            eth_dst="ff:ff:ff:ff:ff:ff",
            eth_src=self.tp10_dyn_mac,
            dl_vlan_enable=True,
            vlan_vid=self.vlan10_id,
            pktlen=104,
        )
        tag_vlan20_pkt = simple_udp_packet(
            eth_dst="ff:ff:ff:ff:ff:ff",
            eth_src=self.tp20_dyn_mac,
            dl_vlan_enable=True,
            vlan_vid=self.vlan20_id,
            pktlen=104,
        )
        send_packet(dataplane, self.trunk_dev_port, tag_vlan10_pkt)
        send_packet(dataplane, self.trunk_dev_port, tag_vlan20_pkt)
        time.sleep(2)
        dataplane.flush()

        for mac in (self.tp10_stat_mac, self.tp10_dyn_mac):
            chck_vlan10_pkt = simple_udp_packet(eth_dst=mac, eth_src=chck_vlan10_mac, pktlen=100)
            chck_vlan10_tag_pkt = simple_udp_packet(
                eth_dst=mac,
                eth_src=chck_vlan10_mac,
                dl_vlan_enable=True,
                vlan_vid=self.vlan10_id,
                pktlen=104,
            )
            send_packet(dataplane, self.dev_port0, chck_vlan10_pkt)
            verify_packets(dataplane, chck_vlan10_tag_pkt, [self.trunk_dev_port])

        for mac in (self.tp20_stat_mac, self.tp20_dyn_mac):
            chck_vlan20_pkt = simple_udp_packet(eth_dst=mac, eth_src=chck_vlan20_mac, pktlen=100)
            chck_vlan20_tag_pkt = simple_udp_packet(
                eth_dst=mac,
                eth_src=chck_vlan20_mac,
                dl_vlan_enable=True,
                vlan_vid=self.vlan20_id,
                pktlen=104,
            )
            send_packet(dataplane, self.dev_port2, chck_vlan20_pkt)
            verify_packets(dataplane, chck_vlan20_tag_pkt, [self.trunk_dev_port])

    def _tear_down_trunk_port(self, npu):
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.trunk_port_bp,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )
        if self.vlan10_member3 is not None:
            npu.remove(self.vlan10_member3)
            self.vlan10_member3 = None
        if self.vlan20_member3 is not None:
            npu.remove(self.vlan20_member3)
            self.vlan20_member3 = None

    def test_flush_static_per_vlan(self, npu, dataplane):
        """
        Description:
        Verify flushing static FDB entries by VLAN (flood + non-flushed forward paths).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush static entries on VLAN 10; verify VLAN10 static MACs flood and other entries forward.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan10, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_STATIC"],
        )
        self._verify_flood(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_dynamic_per_vlan(self, npu, dataplane):
        """
        Description:
        Verify flushing dynamic FDB entries by VLAN (flood + forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush dynamic entries on VLAN 10 and verify flooding plus surviving forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan10, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
        )
        self._verify_flood(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_all_per_vlan(self, npu, dataplane):
        """
        Description:
        Verify flushing all FDB entries on VLAN 10 (dual flood passes + VLAN20 forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush all VLAN10 entries; verify stat/dyn floods then VLAN20 forwarding.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan10, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
        )
        chck_mac1 = "00:10:aa:11:11:11"
        chck_mac2 = "00:10:aa:22:22:22"
        self._verify_flood(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [chck_mac1, chck_mac2],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_flood(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [chck_mac1, chck_mac2],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_static_per_port(self, npu, dataplane):
        """
        Description:
        Verify flushing static FDB entries by bridge port (flood + forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush port0 static MAC and verify flood plus non-flushed forwarding matrix.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        flushed_dev_port = self.vlan10_ports[0]
        flushed_mac = self.vlan10_stat_macs[0]
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.vlan10_bps[0], "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_STATIC"],
        )
        self._verify_flood(
            dataplane,
            [flushed_mac],
            self.vlan10_ports,
            [self.vlan10_dyn_macs[1]],
            [self.vlan10_ports[1]],
            self.vlan10_lag_ports,
        )
        not_flushed_ports = [p for p in self.vlan10_ports if p != flushed_dev_port]
        not_flushed_macs = [m for m in self.vlan10_stat_macs if m != flushed_mac]
        self._verify_fwd(
            dataplane,
            not_flushed_macs,
            not_flushed_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_dynamic_per_port(self, npu, dataplane):
        """
        Description:
        Verify flushing dynamic FDB entries by bridge port (flood + forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush port0 dynamic MAC and verify flood plus surviving forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        flushed_dev_port = self.vlan10_ports[0]
        flushed_mac = self.vlan10_dyn_macs[0]
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.vlan10_bps[0], "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
        )
        self._verify_flood(
            dataplane,
            [flushed_mac],
            self.vlan10_ports,
            [self.vlan10_stat_macs[1]],
            [self.vlan10_ports[1]],
            self.vlan10_lag_ports,
        )
        not_flushed_ports = [p for p in self.vlan10_ports if p != flushed_dev_port]
        not_flushed_macs = [m for m in self.vlan10_dyn_macs if m != flushed_mac]
        self._verify_fwd(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            not_flushed_macs,
            not_flushed_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_all_per_port(self, npu, dataplane):
        """
        Description:
        Verify flushing all FDB entries on one bridge port (dual flood + forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush all MACs on port0 and verify both stat/dyn floods and other entries forward.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        flushed_dev_port = self.vlan10_ports[0]
        flushed_stat_mac = self.vlan10_stat_macs[0]
        flushed_dyn_mac = self.vlan10_dyn_macs[0]
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.vlan10_bps[0], "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
        )
        self._verify_flood(
            dataplane,
            [flushed_stat_mac],
            self.vlan10_ports,
            [self.vlan10_dyn_macs[1]],
            [self.vlan10_ports[1]],
            self.vlan10_lag_ports,
        )
        self._verify_flood(
            dataplane,
            [flushed_dyn_mac],
            self.vlan10_ports,
            [self.vlan10_stat_macs[1]],
            [self.vlan10_ports[1]],
            self.vlan10_lag_ports,
        )
        not_flushed_ports = [p for p in self.vlan10_ports if p != flushed_dev_port]
        not_flushed_stat_macs = [m for m in self.vlan10_stat_macs if m != flushed_stat_mac]
        not_flushed_dyn_macs = [m for m in self.vlan10_dyn_macs if m != flushed_dyn_mac]
        self._verify_fwd(
            dataplane,
            not_flushed_stat_macs,
            not_flushed_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            not_flushed_dyn_macs,
            not_flushed_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_static_per_lag(self, npu, dataplane):
        """
        Description:
        Verify flushing static FDB entries by LAG bridge port (flood + forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush LAG1 static MACs and verify flooding plus surviving forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        flushed_dev_ports = self.vlan10_lag_ports
        flushed_macs = [self.vlan10_stat_macs[2], self.vlan10_stat_macs[3], self.vlan10_stat_macs[4]]
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.vlan10_bps[2], "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_STATIC"],
        )
        self._verify_flood(
            dataplane,
            flushed_macs,
            self.vlan10_ports,
            [self.vlan10_dyn_macs[1]],
            [self.vlan10_ports[1]],
            self.vlan10_lag_ports,
        )
        not_flushed_ports = [p for p in self.vlan10_ports if p not in flushed_dev_ports]
        not_flushed_macs = [m for m in self.vlan10_stat_macs if m not in flushed_macs]
        self._verify_fwd(
            dataplane,
            not_flushed_macs,
            not_flushed_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_dynamic_per_lag(self, npu, dataplane):
        """
        Description:
        Verify flushing dynamic FDB entries by LAG bridge port (flood + forward).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush LAG1 dynamic MACs and verify flooding plus surviving forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        flushed_dev_ports = self.vlan10_lag_ports
        flushed_macs = [self.vlan10_dyn_macs[2], self.vlan10_dyn_macs[3], self.vlan10_dyn_macs[4]]
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.vlan10_bps[2], "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
        )
        self._verify_flood(
            dataplane,
            flushed_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[1]],
            [self.vlan10_ports[1]],
            self.vlan10_lag_ports,
        )
        not_flushed_ports = [p for p in self.vlan10_ports if p not in flushed_dev_ports]
        not_flushed_macs = [m for m in self.vlan10_dyn_macs if m not in flushed_macs]
        self._verify_fwd(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            not_flushed_macs,
            not_flushed_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_all_per_lag(self, npu, dataplane):
        """
        Description:
        Match flushAllPerLagTest: dynamic flush by LAG only (PTF omits flood verification here).

        Test scenario:
        1. Prepare mixed static and dynamic FDB entries on VLAN 10 and VLAN 20.
        2. Flush dynamic MACs on LAG1; verify forwarding for entries not flushed.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        flushed_dev_ports = self.vlan10_lag_ports
        flushed_stat_macs = [self.vlan10_stat_macs[2], self.vlan10_stat_macs[3], self.vlan10_stat_macs[4]]
        flushed_dyn_macs = [self.vlan10_dyn_macs[2], self.vlan10_dyn_macs[3], self.vlan10_dyn_macs[4]]
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.vlan10_bps[2], "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
        )
        not_flushed_ports = [p for p in self.vlan10_ports if p not in flushed_dev_ports]
        not_flushed_stat_macs = [m for m in self.vlan10_stat_macs if m not in flushed_stat_macs]
        not_flushed_dyn_macs = [m for m in self.vlan10_dyn_macs if m not in flushed_dyn_macs]
        self._verify_fwd(
            dataplane,
            not_flushed_stat_macs,
            not_flushed_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            not_flushed_dyn_macs,
            not_flushed_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_static_per_vlan_and_port(self, npu, dataplane):
        """
        Description:
        Verify flushing static FDB entries by VLAN and trunk bridge port (trunk setup per PTF).

        Test scenario:
        1. Prepare FDB, configure dual-VLAN trunk on port24, flush static tp10 on trunk.
        2. Verify flood toward trunk and forward checks including tagged trunk paths.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        try:
            self._set_up_trunk_port(npu, dataplane)
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan10,
                    "SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.trunk_port_bp,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_STATIC",
                ],
            )
            self._verify_flood(
                dataplane,
                [self.tp10_stat_mac],
                self.vlan10_ports,
                [self.vlan10_stat_macs[0]],
                [self.dev_port0],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self.vlan10_ports.append(self.trunk_dev_port)
            self.vlan20_ports.append(self.trunk_dev_port)
            self.vlan20_stat_macs.append(self.tp20_stat_mac)
            self.vlan10_dyn_macs.append(self.tp10_dyn_mac)
            self.vlan20_dyn_macs.append(self.tp20_dyn_mac)
            self._verify_fwd(
                dataplane,
                self.vlan10_stat_macs,
                self.vlan10_ports,
                [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
                [self.dev_port0, self.dev_port1],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan20_stat_macs,
                self.vlan20_ports,
                [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
                [self.dev_port2, self.dev_port3],
                self.vlan20_lag_ports,
                self.trunk_dev_port,
                self.vlan20_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan10_dyn_macs,
                self.vlan10_ports,
                [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
                [self.dev_port0, self.dev_port1],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan20_dyn_macs,
                self.vlan20_ports,
                [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
                [self.dev_port2, self.dev_port3],
                self.vlan20_lag_ports,
                self.trunk_dev_port,
                self.vlan20_id,
            )
        finally:
            self.vlan10_ports.remove(self.trunk_dev_port)
            self.vlan20_ports.remove(self.trunk_dev_port)
            self.vlan20_stat_macs.remove(self.tp20_stat_mac)
            self.vlan10_dyn_macs.remove(self.tp10_dyn_mac)
            self.vlan20_dyn_macs.remove(self.tp20_dyn_mac)
            self._tear_down_trunk_port(npu)

    def test_flush_dynamic_per_vlan_and_port(self, npu, dataplane):
        """
        Description:
        Verify flushing dynamic FDB entries by VLAN and trunk bridge port.

        Test scenario:
        1. Trunk setup on port24, flush dynamic tp10 on trunk; verify flood and forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        try:
            self._set_up_trunk_port(npu, dataplane)
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan10,
                    "SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.trunk_port_bp,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC",
                ],
            )
            self._verify_flood(
                dataplane,
                [self.tp10_dyn_mac],
                self.vlan10_ports,
                [self.vlan10_stat_macs[0]],
                [self.dev_port0],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self.vlan10_ports.append(self.trunk_dev_port)
            self.vlan20_ports.append(self.trunk_dev_port)
            self.vlan10_stat_macs.append(self.tp10_stat_mac)
            self.vlan20_stat_macs.append(self.tp20_stat_mac)
            self.vlan20_dyn_macs.append(self.tp20_dyn_mac)
            self._verify_fwd(
                dataplane,
                self.vlan10_stat_macs,
                self.vlan10_ports,
                [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
                [self.dev_port0, self.dev_port1],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan20_stat_macs,
                self.vlan20_ports,
                [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
                [self.dev_port2, self.dev_port3],
                self.vlan20_lag_ports,
                self.trunk_dev_port,
                self.vlan20_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan10_dyn_macs,
                self.vlan10_ports,
                [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
                [self.dev_port0, self.dev_port1],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan20_dyn_macs,
                self.vlan20_ports,
                [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
                [self.dev_port2, self.dev_port3],
                self.vlan20_lag_ports,
                self.trunk_dev_port,
                self.vlan20_id,
            )
        finally:
            self.vlan10_ports.remove(self.trunk_dev_port)
            self.vlan20_ports.remove(self.trunk_dev_port)
            self.vlan10_stat_macs.remove(self.tp10_stat_mac)
            self.vlan20_stat_macs.remove(self.tp20_stat_mac)
            self.vlan20_dyn_macs.remove(self.tp20_dyn_mac)
            self._tear_down_trunk_port(npu)

    def test_flush_all_per_vlan_and_port(self, npu, dataplane):
        """
        Description:
        Verify flushing all FDB entries by VLAN and trunk bridge port (dual flood + forward).

        Test scenario:
        1. Trunk on port24; flush all MACs for VLAN10 on trunk; verify stat/dyn floods and forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        chck_vlan10_mac = self.vlan10_stat_macs[0]
        chck_vlan10_port = self.dev_port0
        self._prepare_fdb(npu, dataplane)
        try:
            self._set_up_trunk_port(npu, dataplane)
            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BV_ID", self.vlan10,
                    "SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.trunk_port_bp,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
                ],
            )
            self._verify_flood(
                dataplane,
                [self.tp10_stat_mac],
                self.vlan10_ports,
                [chck_vlan10_mac],
                [chck_vlan10_port],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_flood(
                dataplane,
                [self.tp10_dyn_mac],
                self.vlan10_ports,
                [chck_vlan10_mac],
                [chck_vlan10_port],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self.vlan10_ports.append(self.trunk_dev_port)
            self.vlan20_ports.append(self.trunk_dev_port)
            self.vlan20_stat_macs.append(self.tp20_stat_mac)
            self.vlan20_dyn_macs.append(self.tp20_dyn_mac)
            self._verify_fwd(
                dataplane,
                self.vlan10_stat_macs,
                self.vlan10_ports,
                [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
                [self.dev_port0, self.dev_port1],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan20_stat_macs,
                self.vlan20_ports,
                [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
                [self.dev_port2, self.dev_port3],
                self.vlan20_lag_ports,
                self.trunk_dev_port,
                self.vlan20_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan10_dyn_macs,
                self.vlan10_ports,
                [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
                [self.dev_port0, self.dev_port1],
                self.vlan10_lag_ports,
                self.trunk_dev_port,
                self.vlan10_id,
            )
            self._verify_fwd(
                dataplane,
                self.vlan20_dyn_macs,
                self.vlan20_ports,
                [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
                [self.dev_port2, self.dev_port3],
                self.vlan20_lag_ports,
                self.trunk_dev_port,
                self.vlan20_id,
            )
        finally:
            self.vlan10_ports.remove(self.trunk_dev_port)
            self.vlan20_ports.remove(self.trunk_dev_port)
            self.vlan20_stat_macs.remove(self.tp20_stat_mac)
            self.vlan20_dyn_macs.remove(self.tp20_dyn_mac)
            self._tear_down_trunk_port(npu)

    def test_flush_all_static(self, npu, dataplane):
        """
        Description:
        Verify global flush of static FDB entries (dual VLAN floods + dynamic forwards).

        Test scenario:
        1. Flush all static MACs in FDB; verify stat floods then remaining dynamic forwards.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        npu.flush_fdb_entries(npu.switch_oid, ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_STATIC"])
        self._verify_flood(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_flood(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_dyn_macs[0], self.vlan20_dyn_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_all_dynamic(self, npu, dataplane):
        """
        Description:
        Verify global flush of dynamic FDB entries (dual VLAN floods + static forwards).

        Test scenario:
        1. Flush all dynamic MACs; verify dynamic floods then static entry forwarding.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        npu.flush_fdb_entries(npu.switch_oid, ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"])
        self._verify_flood(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [self.vlan10_stat_macs[0], self.vlan10_stat_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_flood(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [self.vlan20_stat_macs[0], self.vlan20_stat_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [self.vlan10_dyn_macs[0], self.vlan10_dyn_macs[1]],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_fwd(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [self.vlan20_dyn_macs[0], self.vlan20_dyn_macs[1]],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )

    def test_flush_all_macs(self, npu, dataplane):
        """
        Description:
        Verify global flush of all FDB entries (four flood passes, no forward stage in PTF).

        Test scenario:
        1. Flush entire FDB; verify unknown-destination flooding on VLAN10 and VLAN20.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        self._prepare_fdb(npu, dataplane)
        chck_vlan10_mac1 = "00:10:aa:11:11:11"
        chck_vlan10_mac2 = "00:10:aa:22:22:22"
        chck_vlan20_mac1 = "00:20:aa:11:11:11"
        chck_vlan20_mac2 = "00:20:aa:22:22:22"
        npu.flush_fdb_entries(npu.switch_oid, ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])
        self._verify_flood(
            dataplane,
            self.vlan10_stat_macs,
            self.vlan10_ports,
            [chck_vlan10_mac1, chck_vlan10_mac2],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_flood(
            dataplane,
            self.vlan10_dyn_macs,
            self.vlan10_ports,
            [chck_vlan10_mac1, chck_vlan10_mac2],
            [self.dev_port0, self.dev_port1],
            self.vlan10_lag_ports,
        )
        self._verify_flood(
            dataplane,
            self.vlan20_stat_macs,
            self.vlan20_ports,
            [chck_vlan20_mac1, chck_vlan20_mac2],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )
        self._verify_flood(
            dataplane,
            self.vlan20_dyn_macs,
            self.vlan20_ports,
            [chck_vlan20_mac1, chck_vlan20_mac2],
            [self.dev_port2, self.dev_port3],
            self.vlan20_lag_ports,
        )


class TestFdbAge:
    """
    Topology for FdbAgeTest: global FDB aging time, extra VLAN10 member on port24,
    static vrf_mac on port24_bp for routed verification traffic toward CPU path.
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        if len(npu.port_oids) < 25:
            pytest.skip("FdbAgeTest requires physical port index 24 (25 ports)")
        request.cls.vlan_oid = topo.vlan10
        request.cls.vlan_id_int = 10
        request.cls.age_time = 10
        request.cls.vrf_mac = "00:12:34:56:78:90"
        request.cls.vrf_port_dev = 24

        npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", str(request.cls.age_time)])

        port24_oid = npu.port_oids[24]
        port24_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", port24_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        vlan10_member3 = npu.create_vlan_member(
            request.cls.vlan_oid, port24_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED"
        )
        npu.set(port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", str(request.cls.vlan_id_int)])
        npu.create_fdb(request.cls.vlan_oid, request.cls.vrf_mac, port24_bp)

        request.cls._port24_oid = port24_oid
        request.cls._port24_bp = port24_bp
        request.cls._vlan10_member3 = vlan10_member3

        yield

        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )
        npu.remove(request.cls._vlan10_member3)
        npu.remove(request.cls._port24_bp)
        npu.set(request.cls._port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
        npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", "0"])

    def test_mac_aging_on_port(self, npu, dataplane):
        """
        Description:
        Verify dynamic FDB aging for a MAC learned on trunk port1 (macAgingOnPortTest).

        Test scenario:
        1. Learn with tagged traffic from port1; verify untagged delivery on vrf port24.
        2. Verify tagged return to port1; wait age interval then verify VLAN flood.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        lrn_mac = "00:01:01:01:01:01"
        lrn_port = 1
        vrf = self.vrf_port_dev
        lrn_pkt = simple_udp_packet(eth_dst=self.vrf_mac, eth_src=lrn_mac, pktlen=100)
        tag_learn = simple_udp_packet(
            eth_dst=self.vrf_mac, eth_src=lrn_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
        )
        try:
            send_packet(dataplane, lrn_port, tag_learn)
            verify_packets(dataplane, lrn_pkt, [vrf])
            time.sleep(2)

            pkt = simple_udp_packet(eth_dst=lrn_mac, eth_src=self.vrf_mac, pktlen=100)
            tag_pkt = simple_udp_packet(
                eth_dst=lrn_mac, eth_src=self.vrf_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, vrf, pkt)
            verify_packets(dataplane, tag_pkt, [lrn_port])

            _sai_wait_fdb_age(self.age_time)
            send_packet(dataplane, vrf, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt, tag_pkt, pkt],
                [[0], [1], [4, 5, 6]],
            )
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
            )

    def test_mac_aging_on_lag(self, npu, dataplane):
        """
        Description:
        Verify dynamic FDB aging for a MAC learned on LAG1 (macAgingOnLagTest).

        Test scenario:
        1. Learn from LAG member port5; verify return toward LAG from vrf port24.
        2. After aging, verify flood pattern matches PTF.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        lrn_mac = "00:01:01:01:01:01"
        lrn_port = 5
        lag_ports = [4, 5, 6]
        vrf = self.vrf_port_dev
        pkt = simple_udp_packet(eth_dst=self.vrf_mac, eth_src=lrn_mac, pktlen=100)
        try:
            send_packet(dataplane, lrn_port, pkt)
            verify_packets(dataplane, pkt, [vrf])
            time.sleep(2)

            pkt = simple_udp_packet(eth_dst=lrn_mac, eth_src=self.vrf_mac, pktlen=100)
            tag_pkt = simple_udp_packet(
                eth_dst=lrn_mac, eth_src=self.vrf_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, vrf, pkt)
            verify_packet_any_port(dataplane, pkt, lag_ports)

            _sai_wait_fdb_age(self.age_time)
            send_packet(dataplane, vrf, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt, tag_pkt, pkt],
                [[0], [1], [4, 5, 6]],
            )
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
            )

    def test_mac_aging_after_move(self, npu, dataplane):
        """
        Description:
        Aging counted from last move, not initial learn (macAgingAfterMoveTest).

        Test scenario:
        1. Learn on port1, verify; wait 15s; move to port0; verify move.
        2. Wait remainder of old window then verify forward; wait new window then flood.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        age_time = 25
        old_age_out = age_time - 15
        lrn_mac = "00:01:01:01:01:01"
        lrn_port = 1
        mv_port = 0
        vrf = self.vrf_port_dev
        lrn_pkt = simple_udp_packet(eth_dst=self.vrf_mac, eth_src=lrn_mac, pktlen=100)
        lrn_tag_pkt = simple_udp_packet(
            eth_dst=self.vrf_mac, eth_src=lrn_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
        )
        try:
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", str(age_time)])

            send_packet(dataplane, lrn_port, lrn_tag_pkt)
            verify_packets(dataplane, lrn_pkt, [vrf])
            time.sleep(2)

            timer_start = time.time()
            pkt = simple_udp_packet(eth_dst=lrn_mac, eth_src=self.vrf_mac, pktlen=100)
            tag_pkt = simple_udp_packet(
                eth_dst=lrn_mac, eth_src=self.vrf_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, vrf, pkt)
            verify_packets(dataplane, tag_pkt, [lrn_port])

            while time.time() - timer_start < 15:
                time.sleep(1)

            send_packet(dataplane, mv_port, lrn_pkt)
            verify_packets(dataplane, lrn_pkt, [vrf])
            time.sleep(1)
            timer_start = time.time()

            send_packet(dataplane, vrf, pkt)
            verify_packets(dataplane, pkt, [mv_port])

            old_learn_timeout = old_age_out - (time.time() - timer_start)
            _sai_wait_fdb_age(old_learn_timeout)
            send_packet(dataplane, vrf, pkt)
            verify_packets(dataplane, pkt, [mv_port])

            new_learn_timeout = age_time - (time.time() - timer_start)
            _sai_wait_fdb_age(new_learn_timeout)

            send_packet(dataplane, vrf, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt, tag_pkt, pkt],
                [[0], [1], [4, 5, 6]],
            )
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
            )
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", str(self.age_time)])

    def test_mac_move_after_aging(self, npu, dataplane):
        """
        Description:
        Move after prior age clears prior timing (macMoveAfterAgingTest).

        Test scenario:
        1. Learn on port1; wait full age interval; move to port0 and verify.
        2. Wait another age interval and verify flood when dynamic entry is gone.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        lrn_mac = "00:01:01:01:01:01"
        lrn_port = 1
        mv_port = 0
        vrf = self.vrf_port_dev
        lrn_pkt = simple_udp_packet(eth_dst=self.vrf_mac, eth_src=lrn_mac, pktlen=100)
        lrn_tag_pkt = simple_udp_packet(
            eth_dst=self.vrf_mac, eth_src=lrn_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
        )
        try:
            send_packet(dataplane, lrn_port, lrn_tag_pkt)
            verify_packets(dataplane, lrn_pkt, [vrf])
            time.sleep(2)

            _sai_wait_fdb_age(self.age_time)

            send_packet(dataplane, mv_port, lrn_pkt)
            verify_packets(dataplane, lrn_pkt, [vrf])
            time.sleep(1)

            pkt = simple_udp_packet(eth_dst=lrn_mac, eth_src=self.vrf_mac, pktlen=100)
            tag_pkt = simple_udp_packet(
                eth_dst=lrn_mac, eth_src=self.vrf_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104
            )
            send_packet(dataplane, vrf, pkt)
            verify_packets(dataplane, pkt, [mv_port])

            _sai_wait_fdb_age(self.age_time)

            send_packet(dataplane, vrf, pkt)
            verify_each_packet_on_multiple_port_lists(
                dataplane,
                [pkt, tag_pkt, pkt],
                [[0], [1], [4, 5, 6]],
            )
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC"],
            )


class TestFdbMiss:
    """
    Topology for FdbMissTest: VLAN 100 on ports 24–26, hostif trap group (queue 4) with ARP + LLDP traps.
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        if len(npu.port_oids) <= 26:
            pytest.skip("FdbMissTest requires physical port indices 24–26 (27 ports)")
        port24_oid = npu.port_oids[24]
        port25_oid = npu.port_oids[25]
        port26_oid = npu.port_oids[26]

        port24_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", port24_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        port25_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", port25_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        port26_bp = npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", port26_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )

        vlan100 = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100"])
        vm0 = npu.create_vlan_member(vlan100, port24_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vm1 = npu.create_vlan_member(vlan100, port25_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vm2 = npu.create_vlan_member(vlan100, port26_bp, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        npu.set(port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        npu.set(port25_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])
        npu.set(port26_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "100"])

        trap_group = npu.create(
            "SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP",
            ["SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE", "4"],
        )
        arp_trap = npu.create(
            "SAI_OBJECT_TYPE_HOSTIF_TRAP",
            [
                "SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE", "SAI_HOSTIF_TRAP_TYPE_ARP_REQUEST",
                "SAI_HOSTIF_TRAP_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                "SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP", trap_group,
            ],
        )
        lldp_trap = npu.create(
            "SAI_OBJECT_TYPE_HOSTIF_TRAP",
            [
                "SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE", "SAI_HOSTIF_TRAP_TYPE_LLDP",
                "SAI_HOSTIF_TRAP_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                "SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP", trap_group,
            ],
        )

        request.cls.vlan_oid = vlan100
        request.cls.send_port = 24
        request.cls.flood_ports = [25, 26]
        request.cls.src_mac = "00:11:11:11:11:11"
        request.cls.dst_mac = "00:22:22:22:22:22"
        request.cls.mcast_mac = "01:00:5e:11:22:33"
        request.cls.bcast_mac = "ff:ff:ff:ff:ff:ff"
        request.cls.lldp_mac = "01:80:c2:00:00:0e"
        request.cls.ucast_pkt = simple_udp_packet(eth_dst=request.cls.dst_mac, eth_src=request.cls.src_mac)
        request.cls.mcast_pkt = simple_udp_packet(eth_dst=request.cls.mcast_mac, eth_src=request.cls.src_mac)
        request.cls.bcast_pkt = simple_udp_packet(eth_dst=request.cls.bcast_mac, eth_src=request.cls.src_mac)
        request.cls.arp_pkt = simple_arp_packet(arp_op=1, pktlen=100)
        request.cls.lldp_pkt = simple_eth_packet(
            eth_dst=request.cls.lldp_mac, eth_src=request.cls.src_mac, pktlen=60, eth_type=0x88cc
        )

        request.cls._port24_oid = port24_oid
        request.cls._port25_oid = port25_oid
        request.cls._port26_oid = port26_oid
        request.cls._port24_bp = port24_bp
        request.cls._port25_bp = port25_bp
        request.cls._port26_bp = port26_bp
        request.cls._vlan100 = vlan100
        request.cls._vm0 = vm0
        request.cls._vm1 = vm1
        request.cls._vm2 = vm2
        request.cls._trap_group = trap_group
        request.cls._arp_trap = arp_trap
        request.cls._lldp_trap = lldp_trap

        yield

        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
        )
        npu.remove(lldp_trap)
        npu.remove(arp_trap)
        npu.remove(trap_group)

        npu.set(port24_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.set(port25_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.set(port26_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        npu.remove(vm0)
        npu.remove(vm1)
        npu.remove(vm2)
        npu.remove(vlan100)
        npu.remove(port24_bp)
        npu.remove(port25_bp)
        npu.remove(port26_bp)

    def _queue_stat(self, npu, queue_oid):
        return npu.get_stats(queue_oid, ["SAI_QUEUE_STAT_PACKETS", ""]).counters()["SAI_QUEUE_STAT_PACKETS"]

    def _cpu_queue(self, npu, idx):
        cpu_port = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_CPU_PORT", "oid:0x0"], False)[1].oid()
        queues = npu.get_list(cpu_port, "SAI_PORT_ATTR_QOS_QUEUE_LIST", "oid:0x0")
        return queues[idx]

    def _restore_unicast_fwd(self, npu):
        npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
        st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", ""], False)
        assert st == "SAI_STATUS_SUCCESS"
        assert data.value() == "SAI_PACKET_ACTION_FORWARD"

    def _restore_mcast_fwd(self, npu):
        npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
        st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", ""], False)
        assert st == "SAI_STATUS_SUCCESS"
        assert data.value() == "SAI_PACKET_ACTION_FORWARD"

    def _restore_bcast_fwd(self, npu):
        npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
        st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", ""], False)
        assert st == "SAI_STATUS_SUCCESS"
        assert data.value() == "SAI_PACKET_ACTION_FORWARD"

    def test_unicast_miss_drop_action(self, npu, dataplane):
        """
        Description:
        Baseline flood, then drop on unknown unicast when miss action is DROP; restore in finally.

        Test scenario:
        1. Verify default flood; set DROP; verify no packets; restore FORWARD.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.ucast_pkt)
            verify_packets(dataplane, self.ucast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_DROP"
            send_packet(dataplane, self.send_port, self.ucast_pkt)
            verify_no_other_packets(dataplane)
        finally:
            self._restore_unicast_fwd(npu)

    def test_unicast_miss_copy_action(self, npu, dataplane):
        """
        Description:
        Baseline flood, then copy-to-CPU on unknown unicast (queue 0) while flooding (PTF).

        Test scenario:
        1. Baseline flood; set COPY; sleep; measure queue0 delta with flood verification.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.ucast_pkt)
            verify_packets(dataplane, self.ucast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_COPY"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_COPY"
            time.sleep(4)
            q0 = self._cpu_queue(npu, 0)
            pre_stats = self._queue_stat(npu, q0)
            send_packet(dataplane, self.send_port, self.ucast_pkt)
            verify_packets(dataplane, self.ucast_pkt, self.flood_ports)
            time.sleep(4)
            post_stats = self._queue_stat(npu, q0)
            assert post_stats - pre_stats >= 1
            dataplane.flush()
        finally:
            self._restore_unicast_fwd(npu)

    def test_unicast_miss_trap_action(self, npu, dataplane):
        """
        Description:
        Baseline flood then trap unicast miss to CPU queue 0 (PTF).

        Test scenario:
        1. Baseline flood; set TRAP; verify queue0 increments without requiring dataplane flood copy.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.ucast_pkt)
            verify_packets(dataplane, self.ucast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_TRAP"
            time.sleep(4)
            q0 = self._cpu_queue(npu, 0)
            pre_stats = self._queue_stat(npu, q0)
            send_packet(dataplane, self.send_port, self.ucast_pkt)
            time.sleep(4)
            post_stats = self._queue_stat(npu, q0)
            assert post_stats - pre_stats >= 1
            dataplane.flush()
        finally:
            self._restore_unicast_fwd(npu)

    def test_multicast_miss_drop_action(self, npu, dataplane):
        """
        Description:
        Baseline multicast flood, then drop mcast miss; LLDP still hits trap queue 4 (PTF).

        Test scenario:
        1. Flood baseline; DROP mcast miss; verify LLDP still increments queue 4.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.mcast_pkt)
            verify_packets(dataplane, self.mcast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_DROP"
            send_packet(dataplane, self.send_port, self.mcast_pkt)
            verify_no_other_packets(dataplane)
            time.sleep(4)
            q4 = self._cpu_queue(npu, 4)
            pre_stats = self._queue_stat(npu, q4)
            send_packet(dataplane, self.send_port, self.lldp_pkt)
            time.sleep(4)
            post_stats = self._queue_stat(npu, q4)
            assert post_stats - pre_stats >= 1
        finally:
            dataplane.flush()
            self._restore_mcast_fwd(npu)

    def test_multicast_miss_copy_action(self, npu, dataplane):
        """
        Description:
        Multicast miss COPY: flood + queue0; LLDP still uses queue4 (PTF).

        Test scenario:
        1. Baseline flood; COPY; verify mcast flood and CPU copy; then LLDP on queue4.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.mcast_pkt)
            verify_packets(dataplane, self.mcast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_COPY"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_COPY"
            time.sleep(4)
            q0 = self._cpu_queue(npu, 0)
            pre0 = self._queue_stat(npu, q0)
            send_packet(dataplane, self.send_port, self.mcast_pkt)
            verify_packets(dataplane, self.mcast_pkt, self.flood_ports)
            time.sleep(4)
            post0 = self._queue_stat(npu, q0)
            assert post0 - pre0 >= 1
            time.sleep(4)
            q4 = self._cpu_queue(npu, 4)
            pre4 = self._queue_stat(npu, q4)
            send_packet(dataplane, self.send_port, self.lldp_pkt)
            time.sleep(4)
            post4 = self._queue_stat(npu, q4)
            assert post4 - pre4 >= 1
        finally:
            dataplane.flush()
            self._restore_mcast_fwd(npu)

    def test_multicast_miss_trap_action(self, npu, dataplane):
        """
        Description:
        Multicast miss TRAP to queue0 and separate LLDP verification on queue4 (PTF).

        Test scenario:
        1. Baseline flood; TRAP; verify both counters.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.mcast_pkt)
            verify_packets(dataplane, self.mcast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_TRAP"
            time.sleep(4)
            q0 = self._cpu_queue(npu, 0)
            pre0 = self._queue_stat(npu, q0)
            send_packet(dataplane, self.send_port, self.mcast_pkt)
            time.sleep(4)
            post0 = self._queue_stat(npu, q0)
            assert post0 - pre0 >= 1
            time.sleep(4)
            q4 = self._cpu_queue(npu, 4)
            pre4 = self._queue_stat(npu, q4)
            send_packet(dataplane, self.send_port, self.lldp_pkt)
            time.sleep(4)
            post4 = self._queue_stat(npu, q4)
            assert post4 - pre4 >= 1
        finally:
            dataplane.flush()
            self._restore_mcast_fwd(npu)

    def test_broadcast_miss_drop_action(self, npu, dataplane):
        """
        Description:
        Broadcast miss DROP; ARP still trapped to queue 4 (PTF).

        Test scenario:
        1. Baseline bcast flood; DROP; verify ARP still reaches CPU queue 4.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.bcast_pkt)
            verify_packets(dataplane, self.bcast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_DROP"
            send_packet(dataplane, self.send_port, self.bcast_pkt)
            verify_no_other_packets(dataplane)
            time.sleep(4)
            q4 = self._cpu_queue(npu, 4)
            pre_stats = self._queue_stat(npu, q4)
            send_packet(dataplane, self.send_port, self.arp_pkt)
            time.sleep(4)
            post_stats = self._queue_stat(npu, q4)
            assert post_stats - pre_stats >= 1
        finally:
            dataplane.flush()
            self._restore_bcast_fwd(npu)

    def test_broadcast_miss_copy_action(self, npu, dataplane):
        """
        Description:
        Broadcast miss COPY: flood + queue0; ARP still on queue4 (PTF).

        Test scenario:
        1. Baseline flood; COPY bcast miss; verify both stages.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.bcast_pkt)
            verify_packets(dataplane, self.bcast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_COPY"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_COPY"
            time.sleep(4)
            q0 = self._cpu_queue(npu, 0)
            pre0 = self._queue_stat(npu, q0)
            send_packet(dataplane, self.send_port, self.bcast_pkt)
            verify_packets(dataplane, self.bcast_pkt, self.flood_ports)
            time.sleep(4)
            post0 = self._queue_stat(npu, q0)
            assert post0 - pre0 >= 1
            time.sleep(4)
            q4 = self._cpu_queue(npu, 4)
            pre4 = self._queue_stat(npu, q4)
            send_packet(dataplane, self.send_port, self.arp_pkt)
            time.sleep(4)
            post4 = self._queue_stat(npu, q4)
            assert post4 - pre4 >= 1
        finally:
            dataplane.flush()
            self._restore_bcast_fwd(npu)

    def test_broadcast_miss_trap_action(self, npu, dataplane):
        """
        Description:
        Broadcast miss TRAP to queue0; ARP verification on queue4 (PTF).

        Test scenario:
        1. Baseline flood; TRAP; verify queue deltas.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        try:
            send_packet(dataplane, self.send_port, self.bcast_pkt)
            verify_packets(dataplane, self.bcast_pkt, self.flood_ports)
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"])
            st, data = npu.get(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION", ""], False)
            assert st == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_TRAP"
            time.sleep(4)
            q0 = self._cpu_queue(npu, 0)
            pre0 = self._queue_stat(npu, q0)
            send_packet(dataplane, self.send_port, self.bcast_pkt)
            time.sleep(4)
            post0 = self._queue_stat(npu, q0)
            assert post0 - pre0 >= 1
            time.sleep(4)
            q4 = self._cpu_queue(npu, 4)
            pre4 = self._queue_stat(npu, q4)
            send_packet(dataplane, self.send_port, self.arp_pkt)
            time.sleep(4)
            post4 = self._queue_stat(npu, q4)
            assert post4 - pre4 >= 1
        finally:
            dataplane.flush()
            self._restore_bcast_fwd(npu)


class TestFdbEvent:
    """
    Topology for FdbEventTest: validate FDB attributes on learn/age/move/flush/delete.
    """
    @pytest.fixture(scope="class", autouse=True)
    def setup_teardown(self, request, npu, sai_ptf_topology):
        topo = sai_ptf_topology
        request.cls.vlan_oid = topo.vlan10
        request.cls.port0_bp = topo.port0_bp
        request.cls.lag1_bp = topo.lag1_bp
        request.cls.vlan_id_int = 10
        request.cls.src_mac = "00:11:11:11:11:11"
        request.cls.dst_mac = "00:22:22:22:22:22"
        yield
        npu.flush_fdb_entries(
            npu.switch_oid,
            ["SAI_FDB_FLUSH_ATTR_BV_ID", request.cls.vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
        )

    def test_mac_learn_event(self, npu, dataplane):
        """
        Description:
        Verify FDB attributes after a dynamic MAC learning event.

        Test scenario:
        1. Send unknown source traffic to trigger learning on port0.
        2. Verify multi-port flood then read bridge port, packet action, and entry type attributes.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac)
        tag_pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104)
        try:
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [tag_pkt, pkt], [[1], [4, 5, 6]])
            time.sleep(2)
            fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.src_mac)
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.oid() == self.port0_bp
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_FORWARD"
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_FDB_ENTRY_TYPE_DYNAMIC"
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )

    def test_mac_age_event(self, npu, dataplane):
        """
        Description:
        Verify FDB entry removal after aging event.

        Test scenario:
        1. Configure aging time, learn MAC with flood verification, assert attributes before aging.
        2. Wait for expiry and verify FDB get returns item-not-found for the aged entry.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        age_time = 10
        pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac)
        tag_pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104)
        try:
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", str(age_time)])
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [tag_pkt, pkt], [[1], [4, 5, 6]])
            time.sleep(2)
            fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.src_mac)
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.oid() == self.port0_bp
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_FORWARD"
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_FDB_ENTRY_TYPE_DYNAMIC"

            time.sleep(age_time * 2 + 2)
            status, _ = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_ITEM_NOT_FOUND"
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )
            npu.set(npu.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", "0"])

    def test_mac_move_event(self, npu, dataplane):
        """
        Description:
        Verify FDB bridge-port attribute after a MAC move event.

        Test scenario:
        1. Learn MAC on port0 (flood verify and attribute check), move from lag1 member port4.
        2. Verify intermediate move-stage flood and final bridge port on lag1_bp.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac)
        tag_pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104)
        mv_port = 4
        try:
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [tag_pkt, pkt], [[1], [4, 5, 6]])
            time.sleep(2)
            fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.src_mac)
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.oid() == self.port0_bp
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_FORWARD"
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_FDB_ENTRY_TYPE_DYNAMIC"

            send_packet(dataplane, mv_port, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [pkt, tag_pkt], [[0], [1]])
            time.sleep(2)
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.oid() == self.lag1_bp
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_FORWARD"
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_FDB_ENTRY_TYPE_DYNAMIC"
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )

    def test_mac_flush_event(self, npu, dataplane):
        """
        Description:
        Verify FDB entry removal after explicit flush event.

        Test scenario:
        1. Learn dynamic MAC, verify attributes, flush dynamic entries for port0 bridge port.
        2. Verify FDB get returns item-not-found for flushed entry.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac)
        tag_pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104)
        try:
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [tag_pkt, pkt], [[1], [4, 5, 6]])
            time.sleep(2)
            fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.src_mac)
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.oid() == self.port0_bp
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_FORWARD"
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_FDB_ENTRY_TYPE_DYNAMIC"

            npu.flush_fdb_entries(
                npu.switch_oid,
                [
                    "SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", self.port0_bp,
                    "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC",
                ],
            )
            status, _ = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_ITEM_NOT_FOUND"
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )

    def test_mac_delete_event(self, npu, dataplane):
        """
        Description:
        Verify FDB entry removal after explicit delete event.

        Test scenario:
        1. Learn dynamic MAC and verify attributes, then remove FDB entry.
        2. Verify FDB get returns item-not-found for deleted entry.
        """
        if not npu.run_traffic:
            pytest.skip("Traffic generation disabled")
        pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac)
        tag_pkt = simple_udp_packet(eth_dst=self.dst_mac, eth_src=self.src_mac, dl_vlan_enable=True, vlan_vid=self.vlan_id_int, pktlen=104)
        try:
            send_packet(dataplane, 0, pkt)
            verify_each_packet_on_multiple_port_lists(dataplane, [tag_pkt, pkt], [[1], [4, 5, 6]])
            time.sleep(2)
            fdb_key = _fdb_entry_key(npu, self.vlan_oid, self.src_mac)
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.oid() == self.port0_bp
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_PACKET_ACTION_FORWARD"
            status, data = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_SUCCESS"
            assert data.value() == "SAI_FDB_ENTRY_TYPE_DYNAMIC"

            npu.remove(fdb_key)
            status, _ = npu.get(fdb_key, ["SAI_FDB_ENTRY_ATTR_TYPE", ""], False)
            assert status == "SAI_STATUS_ITEM_NOT_FOUND"
        finally:
            npu.flush_fdb_entries(
                npu.switch_oid,
                ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"],
            )

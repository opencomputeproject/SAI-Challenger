import json
import time

import pytest

import saichallenger.topologies.sai_ptf_topology
from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import send_packet, simple_udp_packet, verify_no_other_packets, verify_packet_any_port

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


def _fdb_entry_key(npu, vlan_oid, mac):
    return "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
        {
            "bvid": vlan_oid,
            "mac": mac,
            "switch_id": npu.switch_oid,
        }
    )


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
            pytest.skip("Test requires traffic generation. Run with --traffic")

        assert dataplane is not None, "dataplane is required when running with --traffic"
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
            pytest.skip("Test requires traffic generation. Run with --traffic")

        assert dataplane is not None, "dataplane is required when running with --traffic"
        test_mac = self.macs[0]
        pkt = simple_udp_packet(eth_dst=test_mac)
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
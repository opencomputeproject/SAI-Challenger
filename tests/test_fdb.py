import json
import time

import pytest

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


@pytest.fixture(scope="function")
def fdb_static_mac_topology(npu, sai_ptf_topology):
    """
    Topology for FdbStaticMacTest: provides VLAN 10, lag1, bridge ports and PVIDs.
    """
    topo = sai_ptf_topology
    try:
        yield {
            "vlan_oid": topo.vlan10,
            "vlan_id_int": 10,
            "vlan_id_str": "10",
            "lag_bp_oid": topo.lag1_bp,
            "lag_oid": topo.lag1,
            "lag_member_indices": (4, 5, 6),
            "dev_port0": 0,
            "dev_port1": 1,
            "lag_dev_ports": [4, 5, 6],
            "port0_bp": topo.port0_bp,
            "port1_bp": topo.port1_bp,
        }
    finally:
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", topo.vlan10,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )


def test_fdb_static_mac_forward(npu, dataplane, fdb_static_mac_topology):
    """
    Description:
    Check static FDB forwarding between ports and LAG

    Test scenario:
    1. Retrieve custom VLAN, ports, and LAG from the topology fixture
    2. Create static FDB entries pointing to port 0, port 1, and LAG 1
    3. Send UDP traffic between the ports and verify forwarding to expected destinations
    4. Clean up configuration
    """
    vlan_oid = fdb_static_mac_topology["vlan_oid"]
    vlan_id_int = fdb_static_mac_topology["vlan_id_int"]
    lag_bp_oid = fdb_static_mac_topology["lag_bp_oid"]
    dev_port0 = fdb_static_mac_topology["dev_port0"]
    dev_port1 = fdb_static_mac_topology["dev_port1"]
    lag_dev_ports = fdb_static_mac_topology["lag_dev_ports"]

    macs = []
    for i in range(1, 4):
        macs.append("00:%02d:%02d:%02d:%02d:%02d" % (i, i, i, i, i))

    dst_port_groups = [[dev_port0], [dev_port1], lag_dev_ports]

    try:
        npu.create_fdb(vlan_oid, macs[0], fdb_static_mac_topology["port0_bp"])
        npu.create_fdb(vlan_oid, macs[1], fdb_static_mac_topology["port1_bp"])
        npu.create_fdb(vlan_oid, macs[2], lag_bp_oid)

        if npu.run_traffic:
            assert dataplane is not None, "dataplane is required when running with --traffic"

            for dst_ports, dst_mac in zip(dst_port_groups, macs):
                for src_port, src_mac in zip((dev_port0, dev_port1), macs[:1]):
                    if [src_port] == dst_ports:
                        continue
                    
                    pkt = simple_udp_packet(eth_dst=dst_mac, eth_src=src_mac, pktlen=100)
                    tag_pkt = simple_udp_packet(
                        eth_dst=dst_mac,
                        eth_src=src_mac,
                        dl_vlan_enable=True,
                        vlan_vid=vlan_id_int,
                        pktlen=104,
                    )
                    
                    send_pkt = tag_pkt if src_port == dev_port1 else pkt
                    rcv_pkt = tag_pkt if dst_ports == [dev_port1] else pkt
                    
                    send_packet(dataplane, src_port, send_pkt)
                    verify_packet_any_port(dataplane, rcv_pkt, dst_ports)

    finally:
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )


def test_fdb_self_forwarding_drop(npu, dataplane, fdb_static_mac_topology):
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
    vlan_oid = fdb_static_mac_topology["vlan_oid"]
    dev_port0 = fdb_static_mac_topology["dev_port0"]

    macs = []
    for i in range(1, 4):
        macs.append("00:%02d:%02d:%02d:%02d:%02d" % (i, i, i, i, i))

    try:
        npu.create_fdb(vlan_oid, macs[0], fdb_static_mac_topology["port0_bp"])

        if npu.run_traffic:
            assert dataplane is not None, "dataplane is required when running with --traffic"

            test_mac = macs[0]
            pkt = simple_udp_packet(eth_dst=test_mac)
            send_packet(dataplane, dev_port0, pkt)
            verify_no_other_packets(dataplane)

    finally:
        npu.flush_fdb_entries(
            npu.switch_oid,
            [
                "SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid,
                "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL",
            ],
        )
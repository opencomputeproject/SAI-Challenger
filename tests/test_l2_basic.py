import ipaddress
import pytest
import time
from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_packet, verify_no_packet_any, verify_no_packet, verify_any_packet_any_port


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))

@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()


def test_l2_access_to_access_vlan(npu, dataplane):
    """
    Description:
    Check access to access VLAN members forwarding

    Test scenario:
    1. Create a VLAN 10
    2. Add two ports as untagged members to the VLAN
    3. Setup static FDB entries for port 1 and port 2
    4. Send a simple untagged packet on port 1 and verify packet on port 2
    5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 2
    vlan_mbr_oids = []

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(max_port):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        vlan_mbr = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
        npu.create_fdb(vlan_oid, macs[idx], npu.dot1q_bp_oids[idx])

    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, pkt, [1])
    finally:
        for idx in range(max_port):
            npu.remove_fdb(vlan_oid, macs[idx])
            npu.remove(vlan_mbr_oids[idx])
            npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

        npu.remove(vlan_oid)


def test_l2_trunk_to_trunk_vlan(npu, dataplane):
    """
    Description:
    Check trunk to trunk VLAN members forwarding

    Test scenario:
    1. Create a VLAN 10
    2. Add two ports as tagged members to the VLAN
    3. Setup static FDB entries for port 1 and port 2
    4. Send a simple vlan tag (10) packet on port 1 and verify packet on port 2
    5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])
    vlan_member1 = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_TAGGED")
    vlan_member2 = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_TAGGED")
    npu.create_fdb(vlan_oid, macs[0], npu.dot1q_bp_oids[0])
    npu.create_fdb(vlan_oid, macs[1], npu.dot1q_bp_oids[1])

    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    dl_vlan_enable=True,
                                    vlan_vid=10,
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, pkt, [1])
    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_STATIC"])
        npu.remove(vlan_member1)
        npu.remove(vlan_member2)
        npu.remove(vlan_oid)


def test_l2_access_to_trunk_vlan(npu, dataplane):
    """
    Description:
    Check access to trunk VLAN members forwarding

    Test scenario:
    1. Create a VLAN 10
    2. Add a untagged interfaces for port 1 and  tagged interface for port 2 as members
    3. Setup static FDB entries for port 1 and port 2
    4. Send a simple untagged packet on port 1 and verify packet on port 2 (w/ Vlan 10)
    5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[0])
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_TAGGED")
    npu.set(npu.port_oids[0], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    for idx in range(2):
        npu.create_fdb(vlan_oid, macs[idx], npu.dot1q_bp_oids[idx])

    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=102,
                                    ip_ttl=64)
            exp_pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    dl_vlan_enable=True,
                                    vlan_vid=10,
                                    ip_id=102,
                                    ip_ttl=64,
                                    pktlen=104)
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt, [1])
    finally:
        for idx in range(2):
            npu.remove_fdb(vlan_oid, macs[idx])
            npu.remove_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx])
        npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(npu.port_oids[0], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
        npu.remove(vlan_oid)


def test_l2_trunk_to_access_vlan(npu, dataplane):
    """
    Description:
    Check trunk to access VLAN members forwarding

    Test scenario:
    1. Create a VLAN 10
    2. Add a tagged interfaces for port 1 and  untagged interface for port 2 as members
    3. Setup static FDB entries for port 1 and port 2
    4. Send a simple tagged packet on port 1 and verify packet on port 2 (untagged)
    5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_TAGGED")
    npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[1])
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.set(npu.port_oids[1], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    for idx in range(2):
        npu.create_fdb(vlan_oid, macs[idx], npu.dot1q_bp_oids[idx])

    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    dl_vlan_enable=True,
                                    vlan_vid=10,
                                    ip_id=102,
                                    ip_ttl=64,
                                    pktlen=104)
            exp_pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=102,
                                    ip_ttl=64)
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, exp_pkt, [1])
    finally:
        for idx in range(2):
            npu.remove_fdb(vlan_oid, macs[idx])
            npu.remove_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx])
        npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(npu.port_oids[1], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
        npu.remove(vlan_oid)


def test_l2_flood(npu, dataplane):
    """
    Description:
    Test that the packet received on a port is flooded to all VLAN members

    Test scenario:
    1. Create a VLAN 10
    2. Add three ports as untagged members to the VLAN
    3. Send packet on each port and verify that it only shows up on the other two ports
    4. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    vlan_mbr_oids = []

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(3):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        vlan_mbr = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=107,
                                    ip_ttl=64)

            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, pkt, [1, 2])
            send_packet(dataplane, 1, pkt)
            verify_packets(dataplane, pkt, [0, 2])
            send_packet(dataplane, 2, pkt)
            verify_packets(dataplane, pkt, [0, 1])
    finally:
        for idx in range(3):
            npu.remove(vlan_mbr_oids[idx])
            npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
        npu.remove(vlan_oid)


def test_l2_lag(npu, dataplane):
    """
    Description:
    Check that the packets are equally divided among LAG members.

    Test scenario:
    1. Remove three bridge ports from default .1Q bridge
    2. Remove port 4 from the default VLAN
    3. Create a LAG group with 3 ports
    4. Create a VLAN 10 and VLAN members
    5. Set PVID for LAG and port 4
    6. Setup static FDB entries for port 4 and the LAG with unique MAC addresses
    7. Send packets with varying ip addresses and check count of packets received in ports 1 through 3
    8. Verify that the counts are around divided equally amongst ports with a margin of error 10%
    9. Send packets from each of the members and check they are received on port 4 (with port 4's destination MAC)
    10. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 3
    lag_mbr_oids = []

    # Remove bridge ports
    for idx in range(max_port):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        npu.remove(npu.dot1q_bp_oids[idx])

    # Remove Port #3 from the default VLAN
    npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[3])

    # Create LAG
    lag_oid = npu.create(SaiObjType.LAG, [])

    # Create LAG members
    for idx in range(max_port):
        oid = npu.create(SaiObjType.LAG_MEMBER,
                         [
                             "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                             "SAI_LAG_MEMBER_ATTR_PORT_ID", npu.port_oids[idx]
                         ])
        lag_mbr_oids.append(oid)

    # Create bridge port for LAG
    lag_bp_oid = npu.create(SaiObjType.BRIDGE_PORT,
                            [
                                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                "SAI_BRIDGE_PORT_ATTR_PORT_ID", lag_oid,
                                #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", npu.dot1q_br_oid,
                                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                            ])

    # Create VLAN
    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    # Create VLAN members
    npu.create_vlan_member(vlan_oid, lag_bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[3], "SAI_VLAN_TAGGING_MODE_UNTAGGED")

    # Set PVID for LAG and Port #3
    npu.set(npu.port_oids[3], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
    npu.set(lag_oid, ["SAI_LAG_ATTR_PORT_VLAN_ID", vlan_id])

    npu.create_fdb(vlan_oid, macs[0], lag_bp_oid)
    npu.create_fdb(vlan_oid, macs[1], npu.dot1q_bp_oids[3])

    try:
        if npu.run_traffic:
            count = [0, 0, 0]
            dst_ip = ipaddress.IPv4Address('10.10.10.1')
            max_itrs = 200
            for i in range(0, max_itrs):
                pkt = simple_tcp_packet(eth_dst=macs[0],
                                        eth_src=macs[1],
                                        ip_dst=str(dst_ip),
                                        ip_src='192.168.8.1',
                                        ip_id=109,
                                        ip_ttl=64)

                send_packet(dataplane, 3, pkt)
                rcv_idx = verify_any_packet_any_port(dataplane, [pkt], [0, 1, 2])
                count[rcv_idx] += 1
                dst_ip += 1

            for i in range(0, 3):
                assert(count[i] >= ((max_itrs / 3) * 0.8))

            pkt = simple_tcp_packet(eth_src=macs[0],
                                    eth_dst=macs[1],
                                    ip_dst='10.0.0.1',
                                    ip_id=109,
                                    ip_ttl=64)

            print("Sending packet port 1 (lag member) -> port 4")
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, pkt, [3])
            print("Sending packet port 2 (lag member) -> port 4")
            send_packet(dataplane, 1, pkt)
            verify_packets(dataplane, pkt, [3])
            print("Sending packet port 3 (lag member) -> port 4")
            send_packet(dataplane, 2, pkt)
            verify_packets(dataplane, pkt, [3])
    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])

        npu.remove_vlan_member(vlan_oid, lag_bp_oid)
        npu.remove_vlan_member(vlan_oid, npu.dot1q_bp_oids[3])
        npu.remove(vlan_oid)

        for oid in lag_mbr_oids:
            npu.remove(oid)

        npu.remove(lag_bp_oid)
        npu.remove(lag_oid)

        # Create bridge port for ports removed from LAG
        for idx in range(max_port):
            bp_oid = npu.create(SaiObjType.BRIDGE_PORT,
                                [
                                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", npu.port_oids[idx],
                                    #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", npu.dot1q_br_oid,
                                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                                ])
            npu.dot1q_bp_oids[idx] = bp_oid

        # Add ports to default VLAN
        for oid in npu.dot1q_bp_oids[0:4]:
            npu.create_vlan_member(npu.default_vlan_oid, oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        # Set PVID
        for oid in npu.port_oids[0:4]:
            npu.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_l2_vlan_bcast_ucast(npu, dataplane):
    """
    Description:
    VLAN broadcast and known unicast test.
    Verify the broadcast packet reaches all ports in the VLAN and known unicast packet reaches specific port.

    Test scenario:
    1. Create a VLAN 10
    2. Add ports as untagged members to the VLAN
    3. Add MAC for each port
    4. Send untagged broadcast packet from port 1, verify all ports receive the packet
    5. Send untagged unicast packets from port 1 to the rest of the vlan members ports.
       Verify only one port at a time receives the packet and port n does not.
    6. Clean up configuration
    """
    vlan_id = "10"
    macs = []

    # Create VLAN
    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx, bp_oid in enumerate(npu.dot1q_bp_oids):
        npu.remove_vlan_member(npu.default_vlan_oid, bp_oid)
        npu.create_vlan_member(vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

        macs.append("00:00:00:00:00:%02x" %(idx+1))
        npu.create_fdb(vlan_oid, macs[idx], bp_oid)

    try:
        if npu.run_traffic:
            bcast_pkt = simple_tcp_packet(eth_dst='ff:ff:ff:ff:ff:ff',
                                          eth_src='00:00:00:00:00:01',
                                          ip_dst='10.0.0.1',
                                          ip_id=101,
                                          ip_ttl=64)

            expected_ports = []
            for idx in range(1, len(npu.dot1q_bp_oids)):
                expected_ports.append(idx)

            send_packet(dataplane, 0, bcast_pkt)
            verify_packets(dataplane, bcast_pkt, expected_ports)

            for idx in range(1, len(npu.dot1q_bp_oids)):
                ucast_pkt = simple_tcp_packet(eth_dst=macs[idx],
                                              eth_src='00:00:00:00:00:01',
                                              ip_dst='10.0.0.1',
                                              ip_id=101,
                                              ip_ttl=64)

                send_packet(dataplane, 0, ucast_pkt)
                verify_packets(dataplane, ucast_pkt, [idx])

    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])
        for idx, bp_oid in enumerate(npu.dot1q_bp_oids):
            npu.remove_vlan_member(vlan_oid, bp_oid)
            npu.create_vlan_member(npu.default_vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
        npu.remove(vlan_oid)


def test_l2_mtu(npu, dataplane):
    """
    Description:
    Send untagged packet with max MTU size and verify forwarding.
    Add VLAN tag so that the total packet size exceeds the MTU value and verify behavior.
    Default action is to drop packets exceeding configured MTU value.

    Test scenario:
    1. Create VLAN 10 in the database
    2. Fetch the MTU for the port P1, P2, P3
    3. Create two member port (port P1 and P2) as untagged port and port P3 as tagged port of vlan 10
    4. Set MTU size 1500 for port P1, P2 and P3
    5. Set the Port VLAN ID 10 for port P1, P2 and P3
    6. Send untagged TCP packet of size 1400 bytes on port 1.
    7. Untagged packet of size 1400 should be received at port 2 and tagged packet of vlan 10 should be received at port 3.
    8. Send untagged TCP packet of size 1500 bytes on port 1.
    9. Untagged packet of size 1500 should be received at port 2 and tagged packet of vlan 10 should not be received at port 3.
    10. Clean up configuration
    """
    vlan_id = "10"
    port_mtu = "1500"
    port_default_mtu = []
    max_port = 3

    for oid in npu.port_oids[0:max_port]:
        mtu = npu.get(oid, ["SAI_PORT_ATTR_MTU", ""]).value()
        port_default_mtu.append(mtu)

    for oid in npu.dot1q_bp_oids[0:max_port]:
        npu.remove_vlan_member(npu.default_vlan_oid, oid)

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[2], "SAI_VLAN_TAGGING_MODE_TAGGED")

    for oid in npu.port_oids[0:max_port]:
        npu.set(oid, ["SAI_PORT_ATTR_MTU", port_mtu])
        npu.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(pktlen=1400,
                                    eth_dst='00:22:22:22:22:22',
                                    eth_src='00:11:11:11:11:11',
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            tag_pkt = simple_tcp_packet(pktlen=1404,
                                        eth_dst='00:22:22:22:22:22',
                                        eth_src='00:11:11:11:11:11',
                                        dl_vlan_enable=True,
                                        vlan_vid=int(vlan_id),
                                        ip_dst='10.0.0.1',
                                        ip_id=101,
                                        ip_ttl=64)

            pkt1 = simple_tcp_packet(pktlen=1500,
                                     eth_dst='00:22:22:22:22:22',
                                     eth_src='00:11:11:11:11:11',
                                     ip_dst='10.0.0.1',
                                     ip_id=101,
                                     ip_ttl=64)

            tag_pkt1 = simple_tcp_packet(pktlen=1504,
                                         eth_dst='00:22:22:22:22:22',
                                         eth_src='00:11:11:11:11:11',
                                         dl_vlan_enable=True,
                                         vlan_vid=int(vlan_id),
                                         ip_dst='10.0.0.1',
                                         ip_id=101,
                                         ip_ttl=64)

            send_packet(dataplane, 0, pkt)
            verify_packet(dataplane, pkt, 1)
            verify_packet(dataplane, tag_pkt, 2)

            send_packet(dataplane, 0, pkt1)
            verify_packet(dataplane, pkt1, 1)
            verify_no_packet(dataplane, tag_pkt1, 2)

    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])
        for idx, oid in enumerate(npu.port_oids[0:max_port]):
            npu.remove_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx])
            npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            npu.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])
            npu.set(oid, ["SAI_PORT_ATTR_MTU", port_default_mtu[idx]])
        npu.remove(vlan_oid)


def test_fdb_bulk_create(npu, dataplane):
    """
    Description:
    Bulk create FDB entries and check with the traffic.

    Test scenario:
    1. Bulk create FDB entries
    2. Check no flooding for created FDB entries
    3. Check flooding if no FDB entry
    4. Flush all entries by VLAN
    """
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22',
            '00:33:33:33:33:33', '00:44:44:44:44:44']
    entry = {
        "bvid"      : npu.default_vlan_oid,
        "switch_id" : npu.switch_oid,
    }

    keys = []
    for mac in macs:
        entry["mac"] = mac
        keys.append(entry.copy())

    attrs = []
    attrs.append("SAI_FDB_ENTRY_ATTR_TYPE")
    attrs.append("SAI_FDB_ENTRY_TYPE_STATIC")
    attrs.append("SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID")
    attrs.append(npu.dot1q_bp_oids[0])

    npu.bulk_create(SaiObjType.FDB_ENTRY, keys, [attrs])

    try:
        if npu.run_traffic:
            src_mac = '00:00:00:11:22:33'
            dst_mac = '00:00:00:aa:bb:cc'

            # Check no flooding for created FDB entries
            for mac in macs:
                pkt = simple_tcp_packet(eth_dst=mac, eth_src=src_mac)
                send_packet(dataplane, 1, pkt)
                verify_packets(dataplane, pkt, [0])

            # Check flooding if no FDB entry
            pkt = simple_tcp_packet(eth_dst=dst_mac, eth_src=src_mac)
            send_packet(dataplane, 1, pkt)
            egress_ports = list(range(len(npu.port_oids)))
            egress_ports.remove(1)
            verify_packets(dataplane, pkt, egress_ports)
    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", npu.default_vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])


def test_fdb_bulk_remove(npu, dataplane):
    """
    Description:
    Bulk remove FDB entries and check with the traffic.

    Test scenario:
    1. Bulk create FDB entries
    2. Check no flooding for created FDB entries
    3. Bulk remove FDB entries
    4. Check flooding if no FDB entry
    5. Flush all entries by VLAN
    """
    src_mac = '00:00:00:11:22:33'
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22',
            '00:33:33:33:33:33', '00:44:44:44:44:44']

    for mac in macs:
        npu.create_fdb(npu.default_vlan_oid, mac, npu.dot1q_bp_oids[0])

    try:
        if npu.run_traffic:
            # Check no flooding for created FDB entries
            for mac in macs:
                pkt = simple_tcp_packet(eth_dst=mac, eth_src=src_mac)
                send_packet(dataplane, 1, pkt)
                verify_packets(dataplane, pkt, [0])

        # Bulk remove FDB entries
        keys = []
        entry = {
            "bvid"      : npu.default_vlan_oid,
            "switch_id" : npu.switch_oid,
        }
        for mac in macs:
            entry["mac"] = mac
            keys.append(entry.copy())

        npu.bulk_remove(SaiObjType.FDB_ENTRY, keys)

        if npu.run_traffic:
            # Check flooding if no FDB entry
            egress_ports = list(range(len(npu.port_oids)))
            egress_ports.remove(1)
            for mac in macs:
                pkt = simple_tcp_packet(eth_dst=mac, eth_src=src_mac)
                send_packet(dataplane, 1, pkt)
                verify_packets(dataplane, pkt, egress_ports)

    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", npu.default_vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])


def test_l2_mac_move_1(npu, dataplane):
    """
    Description:
    Create VLAN 100 and add member ports 1, 2 and 3. Send packet on port 1 with
    src_mac=MAC1 and dst_mac=MAC2. Verify MAC1 is learnt on port 1 and packet is flooded
    to other member ports (2 and 3 in this example). Send packet on port 2 with src_mac=MAC2
    and dst_mac=MAC1. Verify MAC2 is learnt on port 2. After learning, verify that packet
    from port 1 is only forwarded to port 2 and not to port 3. Repeat the test by sending
    same packet (src_mac=MAC2 and dst_mac=MAC1), on port 3. Verify that station movement
    occurred and MAC2 is learnt on port 3. Packet from port 1 destined to MAC2 must be forwarded
    to port 3 and not to port 2 after the MAC-movement.

    Test scenario:
    1. Create VLAN 100 and associate 3 untagged ports (port 1,2,3) as the member port of VLAN 100
    2. Set attribute value of "Port VLAN ID 100" for the ports 1, 2, 3
    3. Send packet from port 1 with src_mac=MAC1 and dst_mac=MAC2
    4. Send packet from port 2 with src_mac=MAC2 and dst_mac=MAC1
    5. After MAC learning, repeat step 3 and verify that packet from port 1 is only forwarded to port 2 and not to port 3
    6. Send packet (src_mac=MAC2 and dst_mac=MAC1) on port 3
    7. Send packet (src_mac=MAC1 and dst_mac=MAC2) from port 1
    8. Clean up configuration
    """
    vlan_id = "100"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 3
    vlan_mbr_oids = []
    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(max_port):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        vlan_mbr = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    try:
        if npu.run_traffic:

            pkt1 = simple_tcp_packet(eth_dst=macs[1],
                                     eth_src=macs[0],
                                     ip_dst='192.168.0.2',
                                     ip_src='192.168.0.1',
                                     ip_id=105,
                                     ip_ttl=64)

            pkt2 = simple_tcp_packet(eth_dst=macs[0],
                                     eth_src=macs[1],
                                     ip_dst='192.168.0.1',
                                     ip_src='192.168.0.2',
                                     ip_id=105,
                                     ip_ttl=64)
            send_packet(dataplane, 0, pkt1)
            verify_packets(dataplane, pkt1, [1, 2])

            send_packet(dataplane, 1, pkt2)
            verify_packets(dataplane, pkt2, [0])

            time.sleep(1)

            send_packet(dataplane, 0, pkt1)
            verify_packets(dataplane, pkt1, [1])
            verify_no_packet(dataplane, pkt1, 2)

            time.sleep(1)

            send_packet(dataplane, 2, pkt2)
            verify_packets(dataplane, pkt2, [0])

            time.sleep(1)

            send_packet(dataplane, 0, pkt1)
            verify_packets(dataplane, pkt1, [2])
            verify_no_packet(dataplane, pkt1, 1)

    finally:
        npu.flush_fdb_entries(["SAI_FDB_FLUSH_ATTR_BV_ID", vlan_oid, "SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"])
        for idx in range(max_port):
            npu.remove(vlan_mbr_oids[idx])
            npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

        npu.remove(vlan_oid)

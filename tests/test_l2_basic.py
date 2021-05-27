import pytest
from common.switch import SaiObjType
from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_packet, verify_no_packet_any, verify_no_packet, verify_any_packet_any_port


def test_l2_access_to_access_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 2
    vlan_mbr_oids = []

    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(max_port):
        sai.remove_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx])
        vlan_mbr = sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        sai.set(sai.sw.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if sai.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(dataplane, 0, str(pkt))
            verify_packets(dataplane, pkt, [1])
    finally:
        for idx in range(max_port):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove(vlan_mbr_oids[idx])
            sai.create_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            sai.set(sai.sw.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])

        sai.remove(vlan_oid)


def test_l2_trunk_to_trunk_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])
    vlan_member1 = sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_TAGGED")
    vlan_member2 = sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_TAGGED")
    sai.create_fdb(vlan_oid, macs[0], sai.sw.dot1q_bp_oids[0])
    sai.create_fdb(vlan_oid, macs[1], sai.sw.dot1q_bp_oids[1])

    try:
        if sai.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    dl_vlan_enable=True,
                                    vlan_vid=10,
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(dataplane, 0, str(pkt))
            verify_packets(dataplane, pkt, [1])
    finally:
        sai.remove_fdb(vlan_oid, macs[0])
        sai.remove_fdb(vlan_oid, macs[1])
        sai.remove(vlan_member1)
        sai.remove(vlan_member2)
        sai.remove(vlan_oid)


def test_l2_access_to_trunk_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    sai.remove_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[0])
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_TAGGED")
    sai.set(sai.sw.port_oids[0], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    for idx in range(2):
        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if sai.run_traffic:
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
            send_packet(dataplane, 0, str(pkt))
            verify_packets(dataplane, exp_pkt, [1])
    finally:
        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[idx])
        sai.create_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        sai.set(sai.sw.port_oids[0], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
        sai.remove(vlan_oid)


def test_l2_trunk_to_access_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_TAGGED")
    sai.remove_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[1])
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.set(sai.sw.port_oids[1], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    for idx in range(2):
        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if sai.run_traffic:
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
            send_packet(dataplane, 0, str(pkt))
            verify_packets(dataplane, exp_pkt, [1])
    finally:
        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[idx])
        sai.create_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        sai.set(sai.sw.port_oids[1], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
        sai.remove(vlan_oid)


def test_l2_flood(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    vlan_mbr_oids = []

    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(3):
        sai.remove_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx])
        vlan_mbr = sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        sai.set(sai.sw.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    try:
        if sai.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=107,
                                    ip_ttl=64)

            send_packet(dataplane, 0, str(pkt))
            verify_packets(dataplane, pkt, [1, 2])
            send_packet(dataplane, 1, str(pkt))
            verify_packets(dataplane, pkt, [0, 2])
            send_packet(dataplane, 2, str(pkt))
            verify_packets(dataplane, pkt, [0, 1])
    finally:
        for idx in range(3):
            sai.remove(vlan_mbr_oids[idx])
            sai.create_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            sai.set(sai.sw.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
        sai.remove(vlan_oid)


def test_l2_lag(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 3
    lag_mbr_oids = []

    # Remove bridge ports
    for idx in range(max_port):
        sai.remove_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx])
        sai.remove(sai.sw.dot1q_bp_oids[idx])

    # Remove Port #3 from the default VLAN
    sai.remove_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[3])

    # Create LAG
    lag_oid = sai.create(SaiObjType.LAG, [])

    # Create LAG members
    for idx in range(max_port):
        oid = sai.create(SaiObjType.LAG_MEMBER,
                         [
                             "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                             "SAI_LAG_MEMBER_ATTR_PORT_ID", sai.sw.port_oids[idx]
                         ])
        lag_mbr_oids.append(oid)

    # Create bridge port for LAG
    lag_bp_oid = sai.create(SaiObjType.BRIDGE_PORT,
                            [
                                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                "SAI_BRIDGE_PORT_ATTR_PORT_ID", lag_oid,
                                #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", sai.sw.dot1q_br_oid,
                                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                            ])

    # Create VLAN
    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    # Create VLAN members
    sai.create_vlan_member(vlan_oid, lag_bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[3], "SAI_VLAN_TAGGING_MODE_UNTAGGED")

    # Set PVID for LAG and Port #3
    sai.set(sai.sw.port_oids[3], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
    sai.set(lag_oid, ["SAI_LAG_ATTR_PORT_VLAN_ID", vlan_id])

    sai.create_fdb(vlan_oid, macs[0], lag_bp_oid)
    sai.create_fdb(vlan_oid, macs[1], sai.sw.dot1q_bp_oids[3])

    try:
        if sai.run_traffic:
            count = [0, 0, 0]
            dst_ip = int(socket.inet_aton('10.10.10.1').encode('hex'),16)
            max_itrs = 200
            for i in range(0, max_itrs):
                dst_ip_addr = socket.inet_ntoa(hex(dst_ip)[2:].zfill(8).decode('hex'))
                pkt = simple_tcp_packet(eth_dst=macs[0],
                                        eth_src=macs[1],
                                        ip_dst=dst_ip_addr,
                                        ip_src='192.168.8.1',
                                        ip_id=109,
                                        ip_ttl=64)

                send_packet(dataplane, 3, str(pkt))
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
            send_packet(dataplane, 0, str(pkt))
            verify_packets(dataplane, pkt, [3])
            print("Sending packet port 2 (lag member) -> port 4")
            send_packet(dataplane, 1, str(pkt))
            verify_packets(dataplane, pkt, [3])
            print("Sending packet port 3 (lag member) -> port 4")
            send_packet(dataplane, 2, str(pkt))
            verify_packets(dataplane, pkt, [3])
    finally:
        sai.remove_fdb(vlan_oid, macs[0])
        sai.remove_fdb(vlan_oid, macs[1])

        sai.remove_vlan_member(vlan_oid, lag_bp_oid)
        sai.remove_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[3])
        sai.remove(vlan_oid)

        for oid in lag_mbr_oids:
            sai.remove(oid)

        sai.remove(lag_bp_oid)
        sai.remove(lag_oid)

        # Create bridge port for ports removed from LAG
        for idx in range(max_port):
            bp_oid = sai.create(SaiObjType.BRIDGE_PORT,
                                [
                                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", sai.sw.port_oids[idx],
                                    #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", sai.dot1q_br_oid,
                                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                                ])
            sai.sw.dot1q_bp_oids[idx] = bp_oid

        # Add ports to default VLAN
        for oid in sai.sw.dot1q_bp_oids[0:4]:
            sai.create_vlan_member(sai.sw.default_vlan_oid, oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        # Set PVID
        for oid in sai.sw.port_oids[0:4]:
            sai.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])


def test_l2_vlan_bcast_ucast(sai, dataplane):
    vlan_id = "10"
    macs = []

    # Create VLAN
    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx, bp_oid in enumerate(sai.sw.dot1q_bp_oids):
        sai.remove_vlan_member(sai.sw.default_vlan_oid, bp_oid)
        sai.create_vlan_member(vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        sai.set(sai.sw.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

        macs.append("00:00:00:00:00:%02x" %(idx+1))
        sai.create_fdb(vlan_oid, macs[idx], bp_oid)

    try:
        if sai.run_traffic:
            bcast_pkt = simple_tcp_packet(eth_dst='ff:ff:ff:ff:ff:ff',
                                          eth_src='00:00:00:00:00:01',
                                          ip_dst='10.0.0.1',
                                          ip_id=101,
                                          ip_ttl=64)

            expected_ports = []
            for idx in range(len(sai.sw.dot1q_bp_oids)):
                expected_ports.append(idx)

            send_packet(dataplane, 0, str(bcast_pkt))
            verify_packets(dataplane, bcast_pkt, expected_ports)

            for idx, mac in enumerate(macs):
                ucast_pkt = simple_tcp_packet(eth_dst=mac,
                                              eth_src='00:00:00:00:00:01',
                                              ip_dst='10.0.0.1',
                                              ip_id=101,
                                              ip_ttl=64)

                send_packet(dataplane, 0, str(ucast_pkt))
                verify_packets(dataplane, ucast_pkt, [idx])

    finally:
        for idx, bp_oid in enumerate(sai.sw.dot1q_bp_oids):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove_vlan_member(vlan_oid, bp_oid)
            sai.create_vlan_member(sai.sw.default_vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            sai.set(sai.sw.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
        sai.remove(vlan_oid)


def test_l2_mtu(sai, dataplane):
    vlan_id = "10"
    port_mtu = "1500"
    port_default_mtu = []
    max_port = 3

    for oid in sai.sw.port_oids[0:max_port]:
        mtu = sai.get(oid, ["SAI_PORT_ATTR_MTU", ""]).value()
        port_default_mtu.append(mtu)

    for oid in sai.sw.dot1q_bp_oids[0:max_port]:
        sai.remove_vlan_member(sai.sw.default_vlan_oid, oid)

    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.create_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[2], "SAI_VLAN_TAGGING_MODE_TAGGED")

    for oid in sai.sw.port_oids[0:max_port]:
        sai.set(oid, ["SAI_PORT_ATTR_MTU", port_mtu])
        sai.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    try:
        if sai.run_traffic:
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
                                        vlan_vid=vlan_id,
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
                                         vlan_vid=vlan_id,
                                         ip_dst='10.0.0.1',
                                         ip_id=101,
                                         ip_ttl=64)

            send_packet(dataplane, 0, str(pkt))
            verify_packet(dataplane, pkt, 1)
            verify_packet(dataplane, tag_pkt, 2)

            send_packet(dataplane, 0, str(pkt1))
            verify_packet(dataplane, pkt1, 1)
            verify_no_packet(dataplane, tag_pkt1, 2)

    finally:
        for idx, oid in enumerate(sai.sw.port_oids[0:max_port]):
            sai.remove_vlan_member(vlan_oid, sai.sw.dot1q_bp_oids[idx])
            sai.create_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
            sai.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
            sai.set(oid, ["SAI_PORT_ATTR_MTU", port_default_mtu[idx]])
        sai.remove(vlan_oid)

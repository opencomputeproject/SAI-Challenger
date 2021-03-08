import pytest
from common.switch import Sai, SaiObjType
import json

from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_no_packet_any

@pytest.mark.parametrize(
    "fname",
    [
        #"BCM56850/full.rec",
        "BCM56850/empty_sw.rec",
        "BCM56850/bridge_create_1.rec",
        "BCM56850/hostif.rec",
        "BCM56850/acl_tables.rec",
        "BCM56850/bulk_fdb.rec",
        "BCM56850/bulk_route.rec",
        #"BCM56850/tunnel_map.rec",
        "BCM56850/remove_create_port.rec"
    ],
)
def test_apply_sairec(sai, dataplane, fname):
    sai.apply_rec("/sai/sonic-sairedis/tests/" + fname)
    sai.cleanup()


def test_l2_access_to_access_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    port_oids = []

    vlan_oid = sai.get_vid(SaiObjType.VLAN, vlan_id)
    sai.create("SAI_OBJECT_TYPE_VLAN:" + vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(2):
        sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        port_oid = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.sw.dot1q_bp_oids[idx],
                           ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"]).oid()
        sai.set("SAI_OBJECT_TYPE_PORT:" + port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
        port_oids.append(port_oid)

        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if not sai.libsaivs:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(self, 0, str(pkt))
            verify_packets(self, pkt, [1])
    finally:
        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])
            # Set PVID to default VLAN ID
            sai.set("SAI_OBJECT_TYPE_PORT:" + port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
            sai.remove_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx])

        oid = sai.pop_vid(SaiObjType.VLAN, vlan_id)
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + oid)


def test_l2_trunk_to_trunk_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = sai.get_vid(SaiObjType.VLAN, vlan_id)
    sai.create("SAI_OBJECT_TYPE_VLAN:" + vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(2):
        sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_TAGGED")
        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if not sai.libsaivs:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(self, 0, str(pkt))
            verify_packets(self, pkt, [1])
    finally:
        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx])

        oid = sai.pop_vid(SaiObjType.VLAN, vlan_id)
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + oid)


def test_l2_access_to_trunk_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = sai.get_vid(SaiObjType.VLAN, vlan_id)
    sai.create("SAI_OBJECT_TYPE_VLAN:" + vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_TAGGED")

    port_oid = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.sw.dot1q_bp_oids[0],
                       ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"]).oid()
    sai.set("SAI_OBJECT_TYPE_PORT:" + port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    for idx in range(2):
        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if not sai.libsaivs:
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
            send_packet(self, 0, str(pkt))
            verify_packets(self, exp_pkt, [1])
    finally:
        # Set PVID to default VLAN ID
        sai.set("SAI_OBJECT_TYPE_PORT:" + port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])

        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx])

        oid = sai.pop_vid(SaiObjType.VLAN, vlan_id)
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + oid)


def test_l2_trunk_to_access_vlan(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    vlan_oid = sai.get_vid(SaiObjType.VLAN, vlan_id)
    sai.create("SAI_OBJECT_TYPE_VLAN:" + vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_TAGGED")
    sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[1], "SAI_VLAN_TAGGING_MODE_UNTAGGED")

    port_oid = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.sw.dot1q_bp_oids[1],
                       ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"]).oid()
    sai.set("SAI_OBJECT_TYPE_PORT:" + port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])

    for idx in range(2):
        sai.create_fdb(vlan_oid, macs[idx], sai.sw.dot1q_bp_oids[idx])

    try:
        if not sai.libsaivs:
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
            send_packet(self, 0, str(pkt))
            verify_packets(self, exp_pkt, [1])
    finally:
        # Set PVID to default VLAN ID
        sai.set("SAI_OBJECT_TYPE_PORT:" + port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])

        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])
            sai.remove_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx])

        oid = sai.pop_vid(SaiObjType.VLAN, vlan_id)
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + oid)


def test_l2_flood(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    port_oids = []

    vlan_oid = sai.get_vid(SaiObjType.VLAN, vlan_id)
    sai.create("SAI_OBJECT_TYPE_VLAN:" + vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(3):
        sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        port_oid = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.sw.dot1q_bp_oids[idx],
                           ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"]).oid()
        sai.set("SAI_OBJECT_TYPE_PORT:" + port_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
        port_oids.append(port_oid)

    try:
        if not sai.libsaivs:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    ip_dst='10.0.0.1',
                                    ip_id=107,
                                    ip_ttl=64)

            send_packet(self, 0, str(pkt))
            verify_packets(self, pkt, [1, 2])
            send_packet(self, 1, str(pkt))
            verify_packets(self, pkt, [0, 2])
            send_packet(self, 2, str(pkt))
            verify_packets(self, pkt, [0, 1])
    finally:
        for idx in range(3):
            # Set PVID to default VLAN ID
            sai.set("SAI_OBJECT_TYPE_PORT:" + port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])
            sai.remove_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[idx])

        oid = sai.pop_vid(SaiObjType.VLAN, vlan_id)
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + oid)


def test_l2_lag(sai, dataplane):
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    port_oids = []

    # Remove bridge ports
    for oid in sai.sw.dot1q_bp_oids[0:3]:
        port = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid,
                       ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"])
        port_oids.append(port.oid())
        sai.remove("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid)

    # Remove port #3 from the default VLAN
    sai.remove_vlan_member(sai.sw.default_vlan_id, sai.sw.dot1q_bp_oids[3])

    # Create LAG
    lag_oid = sai.get_vid(SaiObjType.LAG, "lag1")
    sai.create("SAI_OBJECT_TYPE_LAG:" + lag_oid, [])

    # Create LAG members
    for oid in port_oids[0:3]:
        lag_mbr_oid = sai.get_vid(SaiObjType.LAG_MEMBER, lag_oid + ',' + oid)
        sai.create("SAI_OBJECT_TYPE_LAG_MEMBER:" + lag_mbr_oid,
                   [
                       "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                       "SAI_LAG_MEMBER_ATTR_PORT_ID", oid
                   ])

    # Create bridge port for LAG
    lag_bp_oid = sai.get_vid(SaiObjType.BRIDGE_PORT, lag_oid)
    sai.create("SAI_OBJECT_TYPE_BRIDGE_PORT:" + lag_bp_oid,
               [
                   "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                   "SAI_BRIDGE_PORT_ATTR_PORT_ID", lag_oid,
                   #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", sai.sw.dot1q_br_oid,
                   "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
               ])

    # Create VLAN
    vlan_oid = sai.get_vid(SaiObjType.VLAN, vlan_id)
    sai.create("SAI_OBJECT_TYPE_VLAN:" + vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    # Create VLAN members
    sai.create_vlan_member(vlan_id, lag_bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    sai.create_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[3], "SAI_VLAN_TAGGING_MODE_UNTAGGED")

    port3_oid = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.sw.dot1q_bp_oids[3],
                        ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"]).oid()
    sai.set("SAI_OBJECT_TYPE_PORT:" + port3_oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
    sai.set("SAI_OBJECT_TYPE_LAG:" + lag_oid, ["SAI_LAG_ATTR_PORT_VLAN_ID", vlan_id])

    sai.create_fdb(vlan_oid, macs[0], lag_bp_oid)
    sai.create_fdb(vlan_oid, macs[1], sai.sw.dot1q_bp_oids[3])

    try:
        if not sai.libsaivs:
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

                send_packet(self, 3, str(pkt))
                rcv_idx = verify_any_packet_any_port(self, [pkt], [0, 1, 2])
                count[rcv_idx] += 1
                dst_ip += 1

            print(count)
            for i in range(0, 3):
                self.assertTrue((count[i] >= ((max_itrs / 3) * 0.8)),
                        "Not all paths are equally balanced")

            pkt = simple_tcp_packet(eth_src=macs[0],
                                    eth_dst=macs[1],
                                    ip_dst='10.0.0.1',
                                    ip_id=109,
                                    ip_ttl=64)

            print("Sending packet port 1 (lag member) -> port 4")
            send_packet(self, 0, str(pkt))
            verify_packets(self, pkt, [3])
            print("Sending packet port 2 (lag member) -> port 4")
            send_packet(self, 1, str(pkt))
            verify_packets(self, pkt, [3])
            print("Sending packet port 3 (lag member) -> port 4")
            send_packet(self, 2, str(pkt))
            verify_packets(self, pkt, [3])
    finally:
        for idx in range(2):
            sai.remove_fdb(vlan_oid, macs[idx])

        sai.remove_vlan_member(vlan_id, lag_bp_oid)
        sai.remove_vlan_member(vlan_id, sai.sw.dot1q_bp_oids[3])
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + sai.pop_vid(SaiObjType.VLAN, vlan_id))

        # Delete LAG members
        for oid in port_oids[0:3]:
            lag_mbr_oid = sai.pop_vid(SaiObjType.LAG_MEMBER, lag_oid + ',' + oid)
            sai.remove("SAI_OBJECT_TYPE_LAG_MEMBER:" + lag_mbr_oid)

        # Delete LAG
        sai.remove("SAI_OBJECT_TYPE_BRIDGE_PORT:" + lag_bp_oid)
        sai.pop_vid(SaiObjType.BRIDGE_PORT, lag_oid)
        sai.remove("SAI_OBJECT_TYPE_LAG:" + lag_oid)
        sai.pop_vid(SaiObjType.LAG, "lag1")

        # Create bridge port for ports removed from LAG
        for idx, oid in enumerate(port_oids):
            bp_oid = sai.get_vid(SaiObjType.BRIDGE_PORT, oid)
            sai.create("SAI_OBJECT_TYPE_BRIDGE_PORT:" + bp_oid,
                       [
                           "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                           "SAI_BRIDGE_PORT_ATTR_PORT_ID", oid,
                           #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", sai.dot1q_br_oid,
                           "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                       ])
            sai.sw.dot1q_bp_oids[idx] = bp_oid

        # Add ports to default VLAN
        for oid in sai.sw.dot1q_bp_oids[0:4]:
            sai.create_vlan_member(sai.sw.default_vlan_id, oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        # Set PVID
        port_oids.append(port3_oid)
        for oid in port_oids:
            sai.set("SAI_OBJECT_TYPE_PORT:" + oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])

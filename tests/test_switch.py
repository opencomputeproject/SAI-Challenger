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
        "BCM56850//tunnel_map.rec",
        "BCM56850/remove_create_port.rec"
    ],
)
def test_apply_sairec(sai, dataplane, fname):
    sai.apply_rec("/sai/sonic-sairedis/tests/" + fname)
    sai.cleanup()


def test_get_default_vrf(sai, dataplane):
    _, data = sai.get("SAI_OBJECT_TYPE_SWITCH:" + sai.sw_oid,
                      ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"])
    assert data.to_json()[0] == 'SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID'


def test_vlan_create(sai, dataplane):
    # Create VLANs
    for vlan in ["100", "200", "300"]:
        oid = sai.get_vid(SaiObjType.VLAN, vlan)
        sai.create("SAI_OBJECT_TYPE_VLAN:" + oid, ["SAI_VLAN_ATTR_VLAN_ID", vlan])

    # Get .1Q bridge OID
    _, dot1q_br = sai.get("SAI_OBJECT_TYPE_SWITCH:" + sai.sw_oid,
                          ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"])

    # Retrieve the list of .1Q bridge ports
    _, bport = sai.get("SAI_OBJECT_TYPE_BRIDGE:" + dot1q_br.oid(),
                       ["SAI_BRIDGE_ATTR_PORT_LIST", sai.make_list(33, "oid:0x0")])
    bport_oid = bport.oids()

    # Create VLAN members
    for mbr in range(3):
        oid = sai.get_vid(SaiObjType.VLAN_MEMBER, "100:" + bport_oid[mbr])
        sai.create("SAI_OBJECT_TYPE_VLAN_MEMBER:" + oid,
                   [
                       "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           sai.get_vid(SaiObjType.VLAN, "100"),
                       "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    bport_oid[mbr],
                       "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", "SAI_VLAN_TAGGING_MODE_TAGGED"
                   ])

    # Create FDB entry
    sai.create('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : sai.get_vid(SaiObjType.VLAN, "100"),
                           "mac"       : "FE:54:00:40:F4:E1",
                           "switch_id" : sai.sw_oid
                       }
                   ),
               [
                   "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                   "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bport_oid[1]
               ])

    # Remove bridge ports
    port_oid = []
    for oid in bport_oid[20:24]:
        _, port = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid,
                          ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"])
        port_oid.append(port.oid())
        sai.remove("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid)

    # Create LAG
    lag_oid = sai.get_vid(SaiObjType.LAG, "lag1")
    sai.create("SAI_OBJECT_TYPE_LAG:" + lag_oid, [])

    # Create LAG members
    for oid in port_oid:
        sai.create("SAI_OBJECT_TYPE_LAG_MEMBER:" + sai.get_vid(SaiObjType.LAG_MEMBER, lag_oid + ',' + oid),
                   [
                       "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                       "SAI_LAG_MEMBER_ATTR_PORT_ID", oid
                   ])

    # Create bridge port for LAG
    sai.create("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.get_vid(SaiObjType.BRIDGE_PORT, lag_oid),
               [
                   "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                   "SAI_BRIDGE_PORT_ATTR_PORT_ID", lag_oid,
                   #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", dot1q_br.oid(),
                   "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
               ])

    # Add LAG to VLAN 100
    oid = sai.get_vid(SaiObjType.VLAN_MEMBER, "100:" + lag_oid)
    sai.create("SAI_OBJECT_TYPE_VLAN_MEMBER:" + oid,
               [
                   "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           sai.get_vid(SaiObjType.VLAN, "100"),
                   "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    sai.get_vid(SaiObjType.BRIDGE_PORT, lag_oid),
                   "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", "SAI_VLAN_TAGGING_MODE_TAGGED"
               ])

    # Create FDB entry for LAG
    sai.create('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : sai.get_vid(SaiObjType.VLAN, "100"),
                           "mac"       : "FE:24:00:20:F4:E9",
                           "switch_id" : sai.sw_oid
                       }
                   ),
               [
                   "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                   "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", sai.get_vid(SaiObjType.BRIDGE_PORT, lag_oid)
               ])

    # TODO: The following logic was added just to test PTF datapath.
    #       It should be fixed as per applied configuration.
    pkt = simple_tcp_packet(eth_dst='00:11:11:11:11:11',
                            eth_src='00:22:22:22:22:22',
                            ip_dst='10.0.0.1',
                            ip_id=101,
                            ip_ttl=64)

    exp_pkt = simple_tcp_packet(eth_dst='00:11:11:11:11:11',
                            eth_src='00:22:22:22:22:22',
                            ip_dst='10.0.0.1',
                            dl_vlan_enable=True,
                            vlan_vid=10,
                            ip_id=102,
                            ip_ttl=64,
                            pktlen=104)

    try:
        send_packet(dataplane, 2, pkt)
        #verify_packets(dataplane, exp_pkt, [1])
        verify_no_packet_any(dataplane, exp_pkt, [1])
    finally:
        pass

def test_vlan_remove(sai):

    vlan_oid = sai.get_vid(SaiObjType.VLAN, "100")

    # Delete FDB entries
    for mac in ["FE:54:00:40:F4:E1", "FE:24:00:20:F4:E9"]:
        sai.remove('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                           {
                               "bvid"      : vlan_oid,
                               "mac"       : mac,
                               "switch_id" : sai.sw_oid
                           }
                       )
                   )

    # Delete VLAN members
    _, vlan_mbr = sai.get("SAI_OBJECT_TYPE_VLAN:" + vlan_oid,
                          ["SAI_VLAN_ATTR_MEMBER_LIST", sai.make_list(33, "oid:0x0")])
    vlan_mbr_oid = vlan_mbr.oids()

    for oid in vlan_mbr_oid:
        _, bport = sai.get("SAI_OBJECT_TYPE_VLAN_MEMBER:" + oid,
                           ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", "oid:0x0"])

        sai.pop_vid(SaiObjType.VLAN_MEMBER, "100:" + bport.oid())
        sai.remove("SAI_OBJECT_TYPE_VLAN_MEMBER:" + oid)

    # Delete VLANs
    for vlan in ["100", "200", "300"]:
        oid = sai.pop_vid(SaiObjType.VLAN, vlan)
        sai.remove("SAI_OBJECT_TYPE_VLAN:" + oid)

    # Delete LAG bridge port
    lag_oid = sai.pop_vid(SaiObjType.LAG, "lag1")
    oid = sai.pop_vid(SaiObjType.BRIDGE_PORT, lag_oid)
    sai.remove("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid)

    # Delete LAG members
    lag_mbr_key = []
    lag_mbr = sai.get_vid(SaiObjType.LAG_MEMBER)
    for item in lag_mbr.items():
        if lag_oid in item[0]:
            lag_mbr_key.append(item[0])

    port_oid = []
    for key in lag_mbr_key:
        oid = sai.pop_vid(SaiObjType.LAG_MEMBER, key)
        sai.remove("SAI_OBJECT_TYPE_LAG_MEMBER:" + oid)
        port_oid.append(key.split(',')[1])

    # NOTE: attr SAI_STATUS_NOT_IMPLEMENTED
    #
    #_, lag_mbr = sai.get("SAI_OBJECT_TYPE_LAG:" + lag_oid,
    #                      ["SAI_LAG_ATTR_PORT_LIST", sai.make_list(4, "oid:0x0")])
    #lag_mbr_oid = lag_mbr.oids()

    #port_oid = []
    #for oid in lag_mbr_oid:
    #    _, port = sai.get("SAI_OBJECT_TYPE_LAG_MEMBER:" + oid,
    #                      ["SAI_LAG_MEMBER_ATTR_PORT_ID", "oid:0x0"])
    #    port_oid.append(port.oid())
    #    sai.remove("SAI_OBJECT_TYPE_LAG_MEMBER:" + oid)

    # Delete LAG
    sai.remove("SAI_OBJECT_TYPE_LAG:" + lag_oid)

    # Create bridge port for ports removed from LAG
    for oid in port_oid:
        sai.create("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.get_vid(SaiObjType.BRIDGE_PORT, oid),
                   [
                       "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                       "SAI_BRIDGE_PORT_ATTR_PORT_ID", oid,
                       # "SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", dot1q_br.oid(),
                       "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                   ])

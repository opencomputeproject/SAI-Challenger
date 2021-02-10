import pytest
from common.switch import Sai, SaiObjType
import json

from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_no_packet_any


def test_rif_create(sai, dataplane):
    # Create VRF1
    vrf_oid1 = sai.get_vid(SaiObjType.VIRTUAL_ROUTER, "vrf1")
    sai.create("SAI_OBJECT_TYPE_VIRTUAL_ROUTER:" + vrf_oid1, [])

    # Create VRF2
    vrf_oid2 = sai.get_vid(SaiObjType.VIRTUAL_ROUTER, "vrf2")
    sai.create("SAI_OBJECT_TYPE_VIRTUAL_ROUTER:" + vrf_oid2, [])

    # Get .1Q bridge OID
    _, dot1q_br = sai.get("SAI_OBJECT_TYPE_SWITCH:" + sai.sw_oid,
                          ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"])

    # Retrieve the list of .1Q  ports
    _, bport = sai.get("SAI_OBJECT_TYPE_BRIDGE:" + dot1q_br.oid(),
                       ["SAI_BRIDGE_ATTR_PORT_LIST", sai.make_list(33, "oid:0x0")])
    bport_oid = bport.oids()

    # Remove ports
    port_oid = []
    for oid in bport_oid[0:3]:
        _, port = sai.get("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid,
                          ["SAI_BRIDGE_PORT_ATTR_PORT_ID", "oid:0x0"])
        port_oid.append(port.oid())
        sai.remove("SAI_OBJECT_TYPE_BRIDGE_PORT:" + oid)

    # Create RIF1

    rif_oid1 = sai.get_vid(SaiObjType.ROUTER_INTERFACE, "rif1")
    sai.create("SAI_OBJECT_TYPE_ROUTER_INTERFACE:" + rif_oid1,
               [
                   'SAI_ROUTER_INTERFACE_ATTR_TYPE', 'SAI_ROUTER_INTERFACE_TYPE_PORT',
                   'SAI_ROUTER_INTERFACE_ATTR_PORT_ID', port_oid[0],
                   'SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID', vrf_oid1,
               ]
               )

    # Create LAG1
    lag_oid = sai.get_vid(SaiObjType.LAG, "lag1")
    sai.create("SAI_OBJECT_TYPE_LAG:" + lag_oid, [])

    # Create LAG1 members
    lag_members_id = []
    for oid in port_oid[1:]:
        sai.create("SAI_OBJECT_TYPE_LAG_MEMBER:" + sai.get_vid(SaiObjType.LAG_MEMBER, lag_oid + ',' + oid),
                   [
                       "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                       "SAI_LAG_MEMBER_ATTR_PORT_ID", oid
                   ])
        lag_members_id.append(oid)

    # LAG members validation
    lag_mbr = sai.get_vid(SaiObjType.LAG_MEMBER)
    mbr_len = len(lag_mbr)
    assert mbr_len == 2
    for x in range(mbr_len):
        assert lag_members_id[x] == list(lag_mbr.keys())[x].split(',')[1]

    # Create RIF2

    rif_oid2 = sai.get_vid(SaiObjType.ROUTER_INTERFACE, "rif2")
    sai.create("SAI_OBJECT_TYPE_ROUTER_INTERFACE:" + rif_oid2,
               [
                   'SAI_ROUTER_INTERFACE_ATTR_TYPE', 'SAI_ROUTER_INTERFACE_TYPE_PORT',
                   'SAI_ROUTER_INTERFACE_ATTR_PORT_ID', lag_oid,
                   'SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID', vrf_oid2,
               ]
               )



def test_rif_remove(sai):
    # Delete RIF1
    rif_oid1 = sai.get_vid(SaiObjType.ROUTER_INTERFACE, "rif1")
    sai.remove("SAI_OBJECT_TYPE_ROUTER_INTERFACE:" + rif_oid1)

    # Delete RIF2
    rif_oid2 = sai.get_vid(SaiObjType.ROUTER_INTERFACE, "rif2")
    sai.remove("SAI_OBJECT_TYPE_ROUTER_INTERFACE:" + rif_oid2)

    # Delete LAG1 members
    lag_oid = sai.get_vid(SaiObjType.LAG, "lag1")
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

    # Delete LAG1
    sai.remove("SAI_OBJECT_TYPE_LAG:" + lag_oid)

    # Delete VRF1
    vrf_oid1 = sai.get_vid(SaiObjType.VIRTUAL_ROUTER, "vrf1")
    sai.remove("SAI_OBJECT_TYPE_VIRTUAL_ROUTER:" + vrf_oid1)

    # Delete VRF2
    vrf_oid2 = sai.get_vid(SaiObjType.VIRTUAL_ROUTER, "vrf2")
    sai.remove("SAI_OBJECT_TYPE_VIRTUAL_ROUTER:" + vrf_oid2)

    # Create bridge port for ports removed from LAG
    for oid in port_oid:
        sai.create("SAI_OBJECT_TYPE_BRIDGE_PORT:" + sai.get_vid(SaiObjType.BRIDGE_PORT, oid),
                   [
                       "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                       "SAI_BRIDGE_PORT_ATTR_PORT_ID", oid,
                       # "SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", dot1q_br.oid(),
                       "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                   ])

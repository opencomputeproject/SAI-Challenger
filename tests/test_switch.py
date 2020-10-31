import pytest
from common.switch import Sai, SaiObjType
import json

@pytest.fixture(scope="module")
def sai():
    return Sai()

def test_switch_create(sai):
    sai.create("SAI_OBJECT_TYPE_SWITCH:" + sai.sw_oid,
               [
                   "SAI_SWITCH_ATTR_INIT_SWITCH",     "true",
                   "SAI_SWITCH_ATTR_SRC_MAC_ADDRESS", "52:54:00:EE:BB:70"
               ])

def test_get_default_vrf(sai):
    _, data = sai.get("SAI_OBJECT_TYPE_SWITCH:" + sai.sw_oid,
                      ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"])
    assert data.to_json()[0] == 'SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID'


def test_vlan_create(sai):
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


def test_vlan_remove(sai):
    # Delete FDB entry
    vlan_oid = sai.get_vid(SaiObjType.VLAN, "100")

    sai.remove('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : "FE:54:00:40:F4:E1",
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


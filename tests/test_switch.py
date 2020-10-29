import pytest
from common.switch import Sai, SaiObjType
import json

@pytest.fixture(scope="module")
def sai():
    return Sai()

def test_switch_create(sai):
    sai.create("SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000",
               '[' +
               '  "SAI_SWITCH_ATTR_INIT_SWITCH",     "true",' +
               '  "SAI_SWITCH_ATTR_SRC_MAC_ADDRESS", "52:54:00:EE:BB:70"' +
               ']')

def test_get_default_vrf(sai):
    status = sai.get("SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000", '["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]')
    assert status[1].split(",")[0][2:-1] == 'SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID'

def test_vlan_create(sai):
    # Create VLANs
    for vlan in ["100", "200", "300"]:
        oid = sai.get_vid(SaiObjType.VLAN, vlan)
        sai.create("SAI_OBJECT_TYPE_VLAN:oid:" + oid, '["SAI_VLAN_ATTR_VLAN_ID", "{}"]'.format(vlan))

    # Get .1Q bridge OID
    status = sai.get("SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000", '["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]')
    br_oid = status[1].split(",")[1][5:-2]

    # Retrieve the list of .1Q bridge ports
    bport_str = "oid:0x0," * 33
    bport_str = bport_str[:-1]
    status = sai.get("SAI_OBJECT_TYPE_BRIDGE:oid:" + br_oid, '["SAI_BRIDGE_ATTR_PORT_LIST", "33:{}"]'.format(bport_str))
    br_attr = json.loads(status[1])
    idx = br_attr[1].index(":") + 1
    bport_oid = br_attr[1][idx:].split(",")

    # Create VLAN members
    for mbr in range(3):
        oid = sai.get_vid(SaiObjType.VLAN_MEMBER, "100:{}".format(bport_oid[mbr]))
        sai.create("SAI_OBJECT_TYPE_VLAN_MEMBER:oid:" + oid,
                   '[' +
                   '  "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           "oid:{}",'.format(sai.get_vid(SaiObjType.VLAN, "100")) +
                   '  "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    "{}",'.format(bport_oid[mbr]) +
                   '  "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", "SAI_VLAN_TAGGING_MODE_TAGGED"' +
                   ']')

def test_vlan_remove(sai):
    # Delete VLAN members
    oid = sai.get_vid(SaiObjType.VLAN, "100")
    vlan_mbr_str = "oid:0x0," * 33
    vlan_mbr_str = vlan_mbr_str[:-1]
    status = sai.get("SAI_OBJECT_TYPE_VLAN:oid:" + oid, '["SAI_VLAN_ATTR_MEMBER_LIST", "33:{}"]'.format(vlan_mbr_str))
    vlan_attr = json.loads(status[1])

    idx = vlan_attr[1].index(":") + 1
    vlan_mbr_oid = vlan_attr[1][idx:].split(",")

    for oid in vlan_mbr_oid:
        status = sai.get("SAI_OBJECT_TYPE_VLAN_MEMBER:" + oid,
                         '["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", "oid:0x0"]')
        bport_oid = status[1].split(",")[1][5:-2]
        sai.pop_vid(SaiObjType.VLAN_MEMBER, "100:{}".format(bport_oid))

        sai.remove("SAI_OBJECT_TYPE_VLAN_MEMBER:" + oid)

    # Delete VLANs
    for vlan in ["100", "200", "300"]:
        oid = sai.pop_vid(SaiObjType.VLAN, vlan)
        sai.remove("SAI_OBJECT_TYPE_VLAN:oid:" + oid)

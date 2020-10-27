import pytest
from common.switch import Sai, SaiObjType

dict_obj_id = {}

@pytest.fixture(scope="module")
def sai():
    return Sai()

def test_switch_create(sai):
    status = sai.create("SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000", '["SAI_SWITCH_ATTR_INIT_SWITCH","true","SAI_SWITCH_ATTR_SRC_MAC_ADDRESS","52:54:00:EE:BB:70"]')
    assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

def test_get_default_vrf(sai):
    status = sai.get("SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000", '["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID","oid:0x0"]')
    assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'
    assert status[1].decode("utf-8").split(",")[0][2:-1] == 'SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID'

def test_vlan_create(sai):
    if SaiObjType.VLAN.name not in dict_obj_id:
        dict_obj_id[SaiObjType.VLAN.name] = {}
    for vlan in ["100", "200", "300"]:
        oid = sai.alloc_vid(SaiObjType.VLAN)
        dict_obj_id[SaiObjType.VLAN.name][vlan] = oid
        status = sai.create("SAI_OBJECT_TYPE_VLAN:oid:" + oid, '["SAI_VLAN_ATTR_VLAN_ID","'+vlan+'"]')
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

def test_vlan_remove(sai):
    for vlan in ["100", "200", "300"]:
        oid = dict_obj_id[SaiObjType.VLAN.name].pop(vlan)
        status = sai.remove("SAI_OBJECT_TYPE_VLAN:oid:" + oid)
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'


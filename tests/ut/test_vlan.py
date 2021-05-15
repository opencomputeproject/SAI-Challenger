import pytest
from common.switch import SaiObjType

@pytest.fixture(scope="module")
def sai_vlan_obj(sai):
    vlan_oid = sai.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", "100"])
    yield vlan_oid
    sai.remove(vlan_oid)


@pytest.mark.parametrize(
    "attr,attr_value",
    [
        ("SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES",                     "0"),
        ("SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES",                     "1024"),
        ("SAI_VLAN_ATTR_STP_INSTANCE",                              "oid:0x0"),
        ("SAI_VLAN_ATTR_LEARN_DISABLE",                             "true"),
        ("SAI_VLAN_ATTR_LEARN_DISABLE",                             "false"),
        ("SAI_VLAN_ATTR_IPV4_MCAST_LOOKUP_KEY_TYPE",                "SAI_VLAN_MCAST_LOOKUP_KEY_TYPE_MAC_DA"),
        ("SAI_VLAN_ATTR_IPV6_MCAST_LOOKUP_KEY_TYPE",                "SAI_VLAN_MCAST_LOOKUP_KEY_TYPE_MAC_DA"),
        ("SAI_VLAN_ATTR_UNKNOWN_NON_IP_MCAST_OUTPUT_GROUP_ID",      "oid:0x0"),
        ("SAI_VLAN_ATTR_UNKNOWN_IPV4_MCAST_OUTPUT_GROUP_ID",        "oid:0x0"),
        ("SAI_VLAN_ATTR_UNKNOWN_IPV6_MCAST_OUTPUT_GROUP_ID",        "oid:0x0"),
        ("SAI_VLAN_ATTR_UNKNOWN_LINKLOCAL_MCAST_OUTPUT_GROUP_ID",   "oid:0x0"),
        ("SAI_VLAN_ATTR_INGRESS_ACL",                               "oid:0x0"),
        ("SAI_VLAN_ATTR_EGRESS_ACL",                                "oid:0x0"),
        ("SAI_VLAN_ATTR_META_DATA",                                 "0"),
        ("SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE",        "SAI_VLAN_FLOOD_CONTROL_TYPE_ALL"),
        ("SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_GROUP",               "oid:0x0"),
        ("SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_CONTROL_TYPE",      "SAI_VLAN_FLOOD_CONTROL_TYPE_ALL"),
        ("SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_GROUP",             "oid:0x0"),
        ("SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE",              "SAI_VLAN_FLOOD_CONTROL_TYPE_ALL"),
        ("SAI_VLAN_ATTR_BROADCAST_FLOOD_GROUP",                     "oid:0x0"),
        ("SAI_VLAN_ATTR_CUSTOM_IGMP_SNOOPING_ENABLE",               "true"),
        ("SAI_VLAN_ATTR_CUSTOM_IGMP_SNOOPING_ENABLE",               "false"),
        ("SAI_VLAN_ATTR_TAM_OBJECT",                                "0:")
    ],
)
def test_set_attr(sai, dataplane, sai_vlan_obj, attr, attr_value):
    if attr == "SAI_VLAN_ATTR_STP_INSTANCE":
        status, data = sai.get(sai.sw_oid, ["SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID", attr_value], False)
        assert status == "SAI_STATUS_SUCCESS"
        attr_value = data.oid()

    status = sai.set(sai_vlan_obj, [attr, attr_value], False)
    assert status == "SAI_STATUS_SUCCESS"

@pytest.mark.parametrize(
    "attr,attr_type",
    [
        ("SAI_VLAN_ATTR_VLAN_ID",                                   "sai_uint16_t"),
        ("SAI_VLAN_ATTR_MEMBER_LIST",                               "sai_object_list_t"),
        ("SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES",                     "sai_uint32_t"),
        ("SAI_VLAN_ATTR_STP_INSTANCE",                              "sai_object_id_t"),
        ("SAI_VLAN_ATTR_LEARN_DISABLE",                             "bool"),
        ("SAI_VLAN_ATTR_IPV4_MCAST_LOOKUP_KEY_TYPE",                "sai_vlan_mcast_lookup_key_type_t"),
        ("SAI_VLAN_ATTR_IPV6_MCAST_LOOKUP_KEY_TYPE",                "sai_vlan_mcast_lookup_key_type_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_NON_IP_MCAST_OUTPUT_GROUP_ID",      "sai_object_id_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_IPV4_MCAST_OUTPUT_GROUP_ID",        "sai_object_id_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_IPV6_MCAST_OUTPUT_GROUP_ID",        "sai_object_id_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_LINKLOCAL_MCAST_OUTPUT_GROUP_ID",   "sai_object_id_t"),
        ("SAI_VLAN_ATTR_INGRESS_ACL",                               "sai_object_id_t"),
        ("SAI_VLAN_ATTR_EGRESS_ACL",                                "sai_object_id_t"),
        ("SAI_VLAN_ATTR_META_DATA",                                 "sai_uint32_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE",        "sai_vlan_flood_control_type_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_GROUP",               "sai_object_id_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_CONTROL_TYPE",      "sai_vlan_flood_control_type_t"),
        ("SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_GROUP",             "sai_object_id_t"),
        ("SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE",              "sai_vlan_flood_control_type_t"),
        ("SAI_VLAN_ATTR_BROADCAST_FLOOD_GROUP",                     "sai_object_id_t"),
        ("SAI_VLAN_ATTR_CUSTOM_IGMP_SNOOPING_ENABLE",               "bool"),
        ("SAI_VLAN_ATTR_TAM_OBJECT",                                "sai_object_list_t")
    ],
)
def test_get_attr(sai, dataplane, sai_vlan_obj, attr, attr_type):
    status, data = sai.get_by_type(sai_vlan_obj, attr, attr_type, do_assert = False)

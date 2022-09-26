import pytest
from sai import SaiObjType

TEST_VLAN_ID = "100"


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dut) > 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


@pytest.fixture(scope="module")
def sai_vlan_obj(npu):
    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", TEST_VLAN_ID])
    yield vlan_oid
    npu.remove(vlan_oid)


@pytest.fixture(scope="module")
def sai_vlan_member(npu, sai_vlan_obj):
    npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[0])
    vlan_mbr_oid = npu.create_vlan_member(sai_vlan_obj, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.set(npu.port_oids[0], ["SAI_PORT_ATTR_PORT_VLAN_ID", TEST_VLAN_ID])
    yield vlan_mbr_oid, sai_vlan_obj
    npu.remove(vlan_mbr_oid)
    npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[0], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.set(npu.port_oids[0], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


vlan_attrs = [
    ("SAI_VLAN_ATTR_VLAN_ID",                                   "sai_uint16_t",                     "100"),
    ("SAI_VLAN_ATTR_MEMBER_LIST",                               "sai_object_list_t",                "0:null"),
    ("SAI_VLAN_ATTR_MAX_LEARNED_ADDRESSES",                     "sai_uint32_t",                     "0"),
    ("SAI_VLAN_ATTR_STP_INSTANCE",                              "sai_object_id_t",                  None),
    ("SAI_VLAN_ATTR_LEARN_DISABLE",                             "bool",                             "false"),
    ("SAI_VLAN_ATTR_IPV4_MCAST_LOOKUP_KEY_TYPE",                "sai_vlan_mcast_lookup_key_type_t", "SAI_VLAN_MCAST_LOOKUP_KEY_TYPE_MAC_DA"),
    ("SAI_VLAN_ATTR_IPV6_MCAST_LOOKUP_KEY_TYPE",                "sai_vlan_mcast_lookup_key_type_t", "SAI_VLAN_MCAST_LOOKUP_KEY_TYPE_MAC_DA"),
    ("SAI_VLAN_ATTR_UNKNOWN_NON_IP_MCAST_OUTPUT_GROUP_ID",      "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_UNKNOWN_IPV4_MCAST_OUTPUT_GROUP_ID",        "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_UNKNOWN_IPV6_MCAST_OUTPUT_GROUP_ID",        "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_UNKNOWN_LINKLOCAL_MCAST_OUTPUT_GROUP_ID",   "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_INGRESS_ACL",                               "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_EGRESS_ACL",                                "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_META_DATA",                                 "sai_uint32_t",                     "0"),
    ("SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE",        "sai_vlan_flood_control_type_t",    "SAI_VLAN_FLOOD_CONTROL_TYPE_ALL"),
    ("SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_GROUP",               "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_CONTROL_TYPE",      "sai_vlan_flood_control_type_t",    "SAI_VLAN_FLOOD_CONTROL_TYPE_ALL"),
    ("SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_GROUP",             "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE",              "sai_vlan_flood_control_type_t",    "SAI_VLAN_FLOOD_CONTROL_TYPE_ALL"),
    ("SAI_VLAN_ATTR_BROADCAST_FLOOD_GROUP",                     "sai_object_id_t",                  "oid:0x0"),
    ("SAI_VLAN_ATTR_CUSTOM_IGMP_SNOOPING_ENABLE",               "bool",                             "false"),
    ("SAI_VLAN_ATTR_TAM_OBJECT",                                "sai_object_list_t",                "0:null"),
]

vlan_member_attrs= [
    ("SAI_VLAN_MEMBER_ATTR_VLAN_ID",           "sai_object_id_t"),
    ("SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    "sai_object_id_t"),
    ("SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", "sai_vlan_tagging_mode_t")
]

vlan_attrs_updated = {}


@pytest.mark.parametrize(
    "attr,attr_type,attr_val",
    vlan_attrs
)
def test_get_before_set_attr(npu, dataplane, sai_vlan_obj, attr, attr_type, attr_val):
    status, data = npu.get_by_type(sai_vlan_obj, attr, attr_type, do_assert=False)
    npu.assert_status_success(status)

    if attr == "SAI_VLAN_ATTR_STP_INSTANCE":
        status, data = npu.get_by_type(npu.oid, "SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID", "sai_object_id_t", False)
        assert status == "SAI_STATUS_SUCCESS"
        attr_val = data.oid()

    assert data.value() == attr_val


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
        ("SAI_VLAN_ATTR_TAM_OBJECT",                                "0:null")
    ]
)
def test_set_attr(npu, dataplane, sai_vlan_obj, attr, attr_value):
    if attr == "SAI_VLAN_ATTR_STP_INSTANCE":
        status, data = npu.get(npu.oid, ["SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID", attr_value], False)
        assert status == "SAI_STATUS_SUCCESS"
        attr_value = data.oid()

    status = npu.set(sai_vlan_obj, [attr, attr_value], False)
    npu.assert_status_success(status)

    vlan_attrs_updated[attr] = attr_value


@pytest.mark.parametrize(
    "attr,attr_type,attr_value",
    vlan_attrs
)
def test_get_after_set_attr(npu, dataplane, sai_vlan_obj, attr, attr_type, attr_value):
    status, data = npu.get_by_type(sai_vlan_obj, attr, attr_type, do_assert=False)
    npu.assert_status_success(status)

    if attr in vlan_attrs_updated:
        assert data.value() == vlan_attrs_updated[attr]
    else:
        assert data.value() == attr_value


@pytest.mark.parametrize(
    "vlan_min,vlan_max",
    [
        (1, 16),
        (1024, 1040),
        (4078, 4094),
        #(1, 4094),
    ]
)
def test_vlan_scaling(npu, dataplane, vlan_min, vlan_max):
    status = "SAI_STATUS_SUCCESS"
    vlan_oids = []

    # Create VLANs
    for vlan_id in range(vlan_min, vlan_max + 1):
        vlan_id = str(vlan_id)
        if vlan_id == TEST_VLAN_ID or vlan_id == npu.default_vlan_id:
            continue
        status, vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id], do_assert = False)
        if status != "SAI_STATUS_SUCCESS":
            break
        vlan_oids.append(vlan_oid)

    # Remove VLANs
    for vlan_oid in vlan_oids:
        npu.remove(vlan_oid)

    assert status == "SAI_STATUS_SUCCESS"


@pytest.mark.parametrize(
    "attr,attr_value,expected_status",
    [
        ("SAI_VLAN_ATTR_VLAN_ID", "101", "!SAI_STATUS_SUCCESS"),
    ]
)
def test_set_attr_negative(npu, dataplane, sai_vlan_obj, attr, attr_value, expected_status):
    status = npu.set(sai_vlan_obj, [attr, attr_value], False)
    if expected_status[0] == "!":
        assert status != expected_status[1:]
    else:
        assert status == expected_status


@pytest.mark.parametrize(
    "vlan_id,expected_status",
    [
        (None,          "SAI_STATUS_MANDATORY_ATTRIBUTE_MISSING"),
        (TEST_VLAN_ID,  "SAI_STATUS_ITEM_ALREADY_EXISTS"),
        ("0",           "!SAI_STATUS_SUCCESS"),
        ("4095",        "!SAI_STATUS_SUCCESS"),
        ("4096",        "SAI_STATUS_INVALID_VLAN_ID"),
    ]
)
def test_vlan_create_negative(npu, dataplane, vlan_id, expected_status):
    attrs = []
    if vlan_id is not None:
        attrs = ["SAI_VLAN_ATTR_VLAN_ID", vlan_id]

    status, vlan_oid = npu.create(SaiObjType.VLAN, attrs, do_assert = False)
    if status == "SAI_STATUS_SUCCESS":
        npu.remove(vlan_oid)

    if expected_status[0] == "!":
        assert status != expected_status[1:]
    else:
        assert status == expected_status


@pytest.mark.parametrize(
    "attr,attr_type",
    vlan_member_attrs
)
def test_vlan_mbr_get_before_set_attr(npu, dataplane, sai_vlan_member, attr, attr_type):
    status, data = npu.get_by_type(sai_vlan_member[0], attr, attr_type, do_assert=False)
    npu.assert_status_success(status)

    if attr == "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID":
        assert data.value() == npu.dot1q_bp_oids[0]
    elif attr == "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE":
        assert data.value() == "SAI_VLAN_TAGGING_MODE_UNTAGGED"
    elif attr == "SAI_VLAN_MEMBER_ATTR_VLAN_ID":
        assert data.value() == sai_vlan_member[1]


@pytest.mark.parametrize(
    "attr,attr_value",
    [
        ("SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE",   "SAI_VLAN_TAGGING_MODE_UNTAGGED"),
        ("SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE",   "SAI_VLAN_TAGGING_MODE_TAGGED"),
        ("SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE",   "SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED")
    ]
)
def test_vlan_member_set(npu, dataplane, sai_vlan_member, attr, attr_value):
    status = npu.set(sai_vlan_member[0], [attr, attr_value], False)
    npu.assert_status_success(status)


@pytest.mark.parametrize(
    "attr,attr_type",
    vlan_member_attrs
)
def test_vlan_mbr_get_after_set_attr(npu, dataplane, sai_vlan_member, attr, attr_type):
    status, data = npu.get_by_type(sai_vlan_member[0], attr, attr_type, do_assert=False)
    npu.assert_status_success(status)


@pytest.mark.parametrize(
    "attr",
    [
        ("SAI_VLAN_MEMBER_ATTR_VLAN_ID"),
        ("SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID")
    ]
)
def test_vlan_mbr_set_negative(npu, dataplane, sai_vlan_member, attr):
    status = ""
    if attr == "SAI_VLAN_MEMBER_ATTR_VLAN_ID":
        status = npu.set(sai_vlan_member[0], [attr, npu.default_vlan_oid], False)
    elif attr == "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID":
        status = npu.set(sai_vlan_member[0], [attr, npu.dot1q_bp_oids[0]], False)
    assert status != "SAI_STATUS_SUCCESS"

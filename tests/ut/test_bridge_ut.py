import pytest
from saichallenger.common.sai_data import SaiObjType


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


bport_attrs = [
    ("SAI_BRIDGE_PORT_ATTR_TYPE",                                           "sai_bridge_port_type_t"),
    ("SAI_BRIDGE_PORT_ATTR_PORT_ID",                                        "sai_object_id_t"),
    ("SAI_BRIDGE_PORT_ATTR_RIF_ID",                                         "sai_object_id_t"),
    ("SAI_BRIDGE_PORT_ATTR_BRIDGE_ID",                                      "sai_object_id_t"),
    ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                              "sai_bridge_port_fdb_learning_mode_t"),
    ("SAI_BRIDGE_PORT_ATTR_MAX_LEARNED_ADDRESSES",                          "sai_uint32_t"),
    ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION",     "sai_packet_action_t"),
    ("SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",                                    "bool"),
    ("SAI_BRIDGE_PORT_ATTR_INGRESS_FILTERING",                              "bool"),
    ("SAI_BRIDGE_PORT_ATTR_EGRESS_FILTERING",                               "bool"),
]

bport_attrs_default = {}
bport_attrs_updated = {}


@pytest.fixture(scope="module")
def sai_bport_obj(npu):
    bport_oid = npu.dot1q_bp_oids[0]
    yield bport_oid

    # Fall back to the defaults
    for attr in bport_attrs_updated:
        if attr in bport_attrs_default:
            npu.set(bport_oid, [attr, bport_attrs_default[attr]])

@pytest.mark.parametrize(
    "attr,attr_type",
    bport_attrs
)
def test_get_before_set_attr(npu, dataplane, sai_bport_obj, attr, attr_type):
    status, data = npu.get_by_type(sai_bport_obj, attr, attr_type, do_assert=False)
    npu.assert_status_success(status)

    if attr == "SAI_BRIDGE_PORT_ATTR_PORT_ID":
        assert data.value() == npu.port_oids[0]


@pytest.mark.parametrize(
    "attr,attr_value",
    [
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                          "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DROP"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                          "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                          "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                          "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_CPU_TRAP"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                          "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_CPU_LOG"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                          "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_FDB_NOTIFICATION"),
        ("SAI_BRIDGE_PORT_ATTR_MAX_LEARNED_ADDRESSES",                      "0"),
        ("SAI_BRIDGE_PORT_ATTR_MAX_LEARNED_ADDRESSES",                      "1024"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_COPY"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_COPY_CANCEL"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_LOG"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_DENY"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION", "SAI_PACKET_ACTION_TRANSIT"),
        ("SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",                                "true"),
        ("SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",                                "false"),
        ("SAI_BRIDGE_PORT_ATTR_INGRESS_FILTERING",                          "true"),
        ("SAI_BRIDGE_PORT_ATTR_INGRESS_FILTERING",                          "false"),
        ("SAI_BRIDGE_PORT_ATTR_EGRESS_FILTERING",                           "true"),
        ("SAI_BRIDGE_PORT_ATTR_EGRESS_FILTERING",                           "false"),
    ],
)
def test_set_attr(npu, dataplane, sai_bport_obj, attr, attr_value):
    status = npu.set(sai_bport_obj, [attr, attr_value], False)
    npu.assert_status_success(status)

    if status == "SAI_STATUS_SUCCESS":
        bport_attrs_updated[attr] = attr_value


@pytest.mark.parametrize(
    "attr,attr_type",
    [
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",                           "sai_bridge_port_fdb_learning_mode_t"),
        ("SAI_BRIDGE_PORT_ATTR_MAX_LEARNED_ADDRESSES",                       "sai_uint32_t"),
        ("SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_LIMIT_VIOLATION_PACKET_ACTION",  "sai_packet_action_t"),
        ("SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",                                 "bool"),
        ("SAI_BRIDGE_PORT_ATTR_INGRESS_FILTERING",                           "bool"),
        ("SAI_BRIDGE_PORT_ATTR_EGRESS_FILTERING",                            "bool"),
    ],
)
def test_get_after_set_attr(npu, dataplane, sai_bport_obj, attr, attr_type):
    status, data = npu.get_by_type(sai_bport_obj, attr, attr_type, do_assert=False)
    npu.assert_status_success(status)

import pytest
from saichallenger.common.sai_data import SaiObjType
from saichallenger.common.sai import Sai

port_attrs = Sai.get_obj_attrs(SaiObjType.PORT)
port_attrs_default = {}
port_attrs_updated = {}


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


@pytest.fixture(scope="module")
def sai_port_obj(npu):
    port_oid = npu.port_oids[0]
    yield port_oid

    # Fall back to the defaults
    for attr in port_attrs_updated:
        if attr in port_attrs_default:
            npu.set(port_oid, [attr, port_attrs_default[attr]])


@pytest.mark.parametrize(
    "attr,attr_type",
    port_attrs
)
def test_get_before_set_attr(npu, dataplane, sai_port_obj, attr, attr_type):#, attr_val):
    status, data = npu.get_by_type(sai_port_obj, attr, attr_type, do_assert = False)
    npu.assert_status_success(status)

    if status == "SAI_STATUS_SUCCESS":
        port_attrs_default[attr] = data.value()

    #assert data.value() == attr_val


@pytest.mark.parametrize(
    "attr,attr_value",
    [
        ("SAI_PORT_ATTR_ADMIN_STATE",               "true"),
        ("SAI_PORT_ATTR_ADMIN_STATE",               "false"),
        ("SAI_PORT_ATTR_PORT_VLAN_ID",              "100"),
        ("SAI_PORT_ATTR_DEFAULT_VLAN_PRIORITY",     "3"),
        ("SAI_PORT_ATTR_DROP_UNTAGGED",             "true"),
        ("SAI_PORT_ATTR_DROP_UNTAGGED",             "false"),
        ("SAI_PORT_ATTR_DROP_TAGGED",               "true"),
        ("SAI_PORT_ATTR_DROP_TAGGED",               "false"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "SAI_PORT_INTERNAL_LOOPBACK_MODE_PHY"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "SAI_PORT_INTERNAL_LOOPBACK_MODE_NONE"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "SAI_PORT_INTERNAL_LOOPBACK_MODE_MAC"),
        ("SAI_PORT_ATTR_UPDATE_DSCP",               "true"),
        ("SAI_PORT_ATTR_UPDATE_DSCP",               "false"),
        ("SAI_PORT_ATTR_MTU",                       "9000"),
        #("SAI_PORT_ATTR_TPID",                      "37120"),   # TPID=0x9100
    ],
)
def test_set_attr(npu, dataplane, sai_port_obj, attr, attr_value):
    status = npu.set(sai_port_obj, [attr, attr_value], False)
    npu.assert_status_success(status)

    if status == "SAI_STATUS_SUCCESS":
        port_attrs_updated[attr] = attr_value


@pytest.mark.parametrize(
    "attr,attr_type",
    [
        ("SAI_PORT_ATTR_ADMIN_STATE",               "bool"),
        ("SAI_PORT_ATTR_PORT_VLAN_ID",              "sai_uint16_t"),
        ("SAI_PORT_ATTR_DEFAULT_VLAN_PRIORITY",     "sai_uint8_t"),
        ("SAI_PORT_ATTR_DROP_UNTAGGED",             "bool"),
        ("SAI_PORT_ATTR_DROP_TAGGED",               "bool"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "sai_port_internal_loopback_mode_t"),
        ("SAI_PORT_ATTR_UPDATE_DSCP",               "bool"),
        ("SAI_PORT_ATTR_MTU",                       "sai_uint32_t"),
        ("SAI_PORT_ATTR_TPID",                      "sai_uint16_t"),
    ]
)
def test_get_after_set_attr(npu, dataplane, sai_port_obj, attr, attr_type):
    status, data = npu.get_by_type(sai_port_obj, attr, attr_type, do_assert = False)
    npu.assert_status_success(status)

    if attr in port_attrs_updated:
        assert data.value() == port_attrs_updated[attr]

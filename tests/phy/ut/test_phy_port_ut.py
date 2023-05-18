import pytest
from saichallenger.common.sai_data import SaiObjType
from saichallenger.common.sai import Sai

port_attrs = Sai.get_obj_attrs(SaiObjType.PORT)
port_attrs_default = {}
port_attrs_updated = {}


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.phy) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


@pytest.fixture(scope="module")
def sai_port_obj(phy):
    port_oid = phy.port_oids[0]
    yield port_oid

    # Fall back to the defaults
    for attr in port_attrs_updated:
        if attr in port_attrs_default:
            phy.set(port_oid, [attr, port_attrs_default[attr]])


@pytest.mark.parametrize(
    "attr,attr_type",
    port_attrs
)
def test_get_before_set_attr(phy, dataplane, sai_port_obj, attr, attr_type):
    status, data = phy.get_by_type(sai_port_obj, attr, attr_type, do_assert = False)
    phy.assert_status_success(status)

    if status == "SAI_STATUS_SUCCESS":
        port_attrs_default[attr] = data.value()


@pytest.mark.parametrize(
    "attr,attr_value",
    [
        ("SAI_PORT_ATTR_ADMIN_STATE",               "true"),
        ("SAI_PORT_ATTR_ADMIN_STATE",               "false"),
        # autoneg, speed and FEC attributes are set from the sku file, for example: phy/broadcom/BCM81724/saivs/sku/8x100g.json
        ("SAI_PORT_ATTR_LOOPBACK_MODE",             "SAI_PORT_LOOPBACK_MODE_PHY_REMOTE"),
        ("SAI_PORT_ATTR_MTU",                       "9000"),
    ],
)
def test_set_attr(phy, dataplane, sai_port_obj, attr, attr_value):
    status = phy.set(sai_port_obj, [attr, attr_value], False)
    phy.assert_status_success(status)

    if status == "SAI_STATUS_SUCCESS":
        port_attrs_updated[attr] = attr_value


@pytest.mark.parametrize(
    "attr,attr_type",
    [
        ("SAI_PORT_ATTR_ADMIN_STATE",               "bool"),
        ("SAI_PORT_ATTR_AUTO_NEG_MODE",             "bool"),
        ("SAI_PORT_ATTR_SPEED",                     "sai_uint32_t"),
        ("SAI_PORT_ATTR_FEC_MODE",                  "sai_uint32_t"),
        ("SAI_PORT_ATTR_LOOPBACK_MODE",             "sai_uint32_t"),
        ("SAI_PORT_ATTR_MTU",                       "sai_uint32_t"),
    ]
)
def test_get_after_set_attr(phy, dataplane, sai_port_obj, attr, attr_type):
    status, data = phy.get_by_type(sai_port_obj, attr, attr_type, do_assert = False)
    phy.assert_status_success(status)

    if attr in port_attrs_updated:
        assert data.value() == port_attrs_updated[attr]

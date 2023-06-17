import pytest
from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiObjType

switch_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_VIRTUAL_ROUTER")


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


class TestDefaultVrf:
    state = dict()

    @pytest.mark.parametrize(
        "attr,attr_type",
        switch_attrs
    )
    def test_get_attr(self, npu, dataplane, attr, attr_type):
        status, data = npu.get_by_type(npu.default_vrf_oid, attr, attr_type, False)
        npu.assert_status_success(status)
        self.state[attr] = data.value()

    @pytest.mark.parametrize(
        "attr,attr_value",
        [
            ("SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "false"),
            ("SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true"),
            ("SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", None),
            ("SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "false"),
            ("SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true"),
            ("SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", None),
            ("SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"),
            ("SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"),
            ("SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION", None),
            ("SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"),
            ("SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"),
            ("SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION", None),
            ("SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"),
            ("SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP"),
            ("SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION", None),
        ],
    )
    def test_set_attr(self, npu, dataplane, attr, attr_value):
        if attr_value is None:
            attr_value = self.state.get(attr)
            if attr_value is None:
                pytest.skip("no default value")
        npu.set(npu.default_vrf_oid, [attr, attr_value])
        assert npu.get(npu.default_vrf_oid, [attr]).value() == attr_value


class TestNonDefaultVrf:
    state = dict()

    @pytest.mark.dependency()
    def test_create(self, npu):
        self.state["vrf_oid"] = npu.create(SaiObjType.VIRTUAL_ROUTER, [])
        assert self.state["vrf_oid"] != "oid:0x0"

    @pytest.mark.parametrize(
        "attr,attr_type",
        switch_attrs
    )
    @pytest.mark.dependency(depends=['TestNonDefaultVrf::test_create'])
    def test_get_attr(self, npu, dataplane, attr, attr_type):
        status, data = npu.get_by_type(self.state["vrf_oid"], attr, attr_type, False)
        npu.assert_status_success(status)

    @pytest.mark.dependency(depends=['TestNonDefaultVrf::test_create'])
    def test_remove(self, npu):
            assert self.state["vrf_oid"] != "oid:0x0"
            npu.remove(self.state["vrf_oid"])

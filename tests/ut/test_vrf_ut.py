import pytest
from sai import Sai
from sai import SaiObjType

switch_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_VIRTUAL_ROUTER")


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dut) > 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


@pytest.mark.parametrize(
    "attr,attr_type",
    switch_attrs
)
def test_default_vrf_get_attr(npu, dataplane, attr, attr_type):
    status, data = npu.get_by_type(npu.default_vrf_oid, attr, attr_type, False)
    npu.assert_status_success(status)


@pytest.fixture(scope="module")
def vrf_state():
    state = {
        "vrf_oid" : "oid:0x0",
    }
    return state

@pytest.mark.dependency()
def test_vrf_create(npu, vrf_state):
    vrf_state["vrf_oid"] = npu.create(SaiObjType.VIRTUAL_ROUTER, [])
    assert vrf_state["vrf_oid"] != "oid:0x0"

@pytest.mark.parametrize(
    "attr,attr_type",
    switch_attrs
)
@pytest.mark.dependency(depends=['test_vrf_create'])
def test_vrf_get_attr(npu, dataplane, vrf_state, attr, attr_type):
    status, data = npu.get_by_type(vrf_state["vrf_oid"], attr, attr_type, False)
    npu.assert_status_success(status)

@pytest.mark.dependency(depends=['test_vrf_create'])
def test_vrf_remove(npu, vrf_state):
        assert vrf_state["vrf_oid"] != "oid:0x0"
        npu.remove(vrf_state["vrf_oid"])

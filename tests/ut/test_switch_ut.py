import pytest
from sai import Sai


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dut) > 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


switch_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_SWITCH")

@pytest.mark.parametrize(
    "attr,attr_type",
    switch_attrs
)
def test_get_attr(npu, dataplane, attr, attr_type):
    status, data = npu.get_by_type(npu.oid, attr, attr_type, do_assert = False)
    npu.assert_status_success(status)

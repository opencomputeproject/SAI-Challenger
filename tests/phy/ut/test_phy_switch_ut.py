import pytest
from saichallenger.common.sai import Sai

switch_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_SWITCH")


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.phy) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


@pytest.mark.parametrize(
    "attr,attr_type",
    switch_attrs
)
def test_get_attr(phy, dataplane, attr, attr_type):
    status, data = phy.get_by_type(phy.switch_oid, attr, attr_type, do_assert = False)
    phy.assert_status_success(status)

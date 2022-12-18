import pytest
from sai import Sai

switch_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_SWITCH")

@pytest.mark.parametrize(
    "attr,attr_type",
    switch_attrs
)
def test_get_attr(npu, dataplane, attr, attr_type):
    status, data = npu.get_by_type(npu.switch_oid, attr, attr_type, do_assert = False)
    npu.assert_status_success(status)

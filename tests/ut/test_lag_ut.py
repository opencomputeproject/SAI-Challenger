import pytest
from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiObjType

lag_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_LAG")
lag_mbr_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_LAG_MEMBER")

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


class TestLag:
    oid = None
    lag_mbr_num = 2
    lag_mbr_oids = []

    @pytest.mark.dependency()
    def test_create(self, npu):
        TestLag.oid = npu.create(SaiObjType.LAG)

    @pytest.mark.parametrize(
        "attr,attr_type",
        lag_attrs
    )
    @pytest.mark.dependency(depends=['TestLag::test_create'])
    def test_get_attr(self, npu, attr, attr_type):
        if attr == "SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID":
            pytest.skip("Valid for SAI_SWITCH_TYPE_VOQ only")
        status, data = npu.get_by_type(TestLag.oid, attr, attr_type, False)
        npu.assert_status_success(status)
        if attr == "SAI_LAG_ATTR_PORT_LIST":
            assert len(data.to_list()) == 0
        elif attr == "SAI_LAG_ATTR_PORT_VLAN_ID":
            assert data.value() == npu.default_vlan_id
        elif attr in ["SAI_LAG_ATTR_DROP_UNTAGGED", "SAI_LAG_ATTR_DROP_TAGGED"]:
            assert data.value() == "false"

    @pytest.mark.dependency(depends=['TestLag::test_create'])
    def test_create_members(self, npu):
        # Remove bridge ports
        for idx in range(TestLag.lag_mbr_num):
            npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
            npu.remove(npu.dot1q_bp_oids[idx])

        # Create LAG members
        for idx in range(TestLag.lag_mbr_num):
            oid = npu.create(SaiObjType.LAG_MEMBER,
                            [
                                "SAI_LAG_MEMBER_ATTR_LAG_ID", TestLag.oid,
                                "SAI_LAG_MEMBER_ATTR_PORT_ID", npu.port_oids[idx]
                            ])
            TestLag.lag_mbr_oids.append(oid)

    @pytest.mark.parametrize(
        "attr,attr_type",
        lag_mbr_attrs
    )
    @pytest.mark.dependency(depends=['TestLag::test_create_members'])
    def test_get_member_attr(self, npu, attr, attr_type):
        status, data = npu.get_by_type(TestLag.lag_mbr_oids[0], attr, attr_type, False)
        npu.assert_status_success(status)
        if attr == "SAI_LAG_MEMBER_ATTR_LAG_ID":
            assert data.value() == TestLag.oid
        elif attr == "SAI_LAG_MEMBER_ATTR_PORT_ID":
            assert data.value() == npu.port_oids[0]
        elif attr in ["SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE", "SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE"]:
            assert data.value() == "false"


    @pytest.mark.dependency(depends=['TestLag::test_create_members'])
    def test_check_members(self, npu):
        status, data = npu.get(TestLag.oid, ["SAI_LAG_ATTR_PORT_LIST"], False)
        npu.assert_status_success(status)
        mbr_oids = data.oids()
        assert len(mbr_oids) == TestLag.lag_mbr_num
        for oid in mbr_oids:
            assert oid in TestLag.lag_mbr_oids

    @pytest.mark.dependency(depends=['TestLag::test_create_members'])
    def test_remove_members(self, npu):
        # Remove LAG members
        for oid in TestLag.lag_mbr_oids:
            npu.remove(oid)

        # Create bridge port for ports removed from LAG
        for idx in range(TestLag.lag_mbr_num):
            bp_oid = npu.create(SaiObjType.BRIDGE_PORT,
                                [
                                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", npu.port_oids[idx],
                                    #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", npu.dot1q_br_oid,
                                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                                ])
            npu.dot1q_bp_oids[idx] = bp_oid

        # Add ports to default VLAN
        for oid in npu.dot1q_bp_oids[0:TestLag.lag_mbr_num]:
            npu.create_vlan_member(npu.default_vlan_oid, oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        # Set PVID
        for oid in npu.port_oids[0:TestLag.lag_mbr_num]:
            npu.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

    @pytest.mark.dependency(depends=['TestLag::test_remove_members'])
    def test_check_no_members(self, npu):
        status, data = npu.get(TestLag.oid, ["SAI_LAG_ATTR_PORT_LIST"], False)
        npu.assert_status_success(status)
        assert len(data.oids()) == 0

    @pytest.mark.dependency(depends=['TestLag::test_create'])
    def test_remove(self, npu):
        npu.remove(TestLag.oid)


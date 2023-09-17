import pytest
import json
from saichallenger.common.sai_data import SaiObjType


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


class TestFdbEntry:
    state = dict()
    mac = "00:00:11:22:33:44"

    @classmethod
    def key(cls, npu, bvid, mac=None):
        key = 'SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : bvid,
                           "mac"       : mac if mac else cls.mac,
                           "switch_id" : npu.switch_oid
                       }
                   )
        return key

    @pytest.mark.dependency()
    def test_create_dynamic(self, npu):
        npu.create_fdb(npu.default_vlan_oid, TestFdbEntry.mac, npu.dot1q_bp_oids[0], "SAI_FDB_ENTRY_TYPE_DYNAMIC")

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_create_duplicated_dynamic(self, npu):
        status, _ = npu.create_fdb(npu.default_vlan_oid, TestFdbEntry.mac, npu.dot1q_bp_oids[0], "SAI_FDB_ENTRY_TYPE_DYNAMIC", do_assert=False)
        assert status == "SAI_STATUS_ITEM_ALREADY_EXISTS"

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_create_duplicated_static(self, npu):
        status, _ = npu.create_fdb(npu.default_vlan_oid, TestFdbEntry.mac, npu.dot1q_bp_oids[0], "SAI_FDB_ENTRY_TYPE_STATIC", do_assert=False)
        assert status == "SAI_STATUS_ITEM_ALREADY_EXISTS"

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_change_to_static(self, npu):
        npu.set(TestFdbEntry.key(npu, npu.default_vlan_oid), ["SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_STATIC"])

    @pytest.mark.dependency(depends=['TestFdbEntry::test_change_to_static'])
    def test_change_to_dynamic(self, npu):
        npu.set(TestFdbEntry.key(npu, npu.default_vlan_oid), ["SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_DYNAMIC"])

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_default_action(self, npu):
        data = npu.get(TestFdbEntry.key(npu, npu.default_vlan_oid), ["SAI_FDB_ENTRY_ATTR_PACKET_ACTION", ""])
        assert data.value() == "SAI_PACKET_ACTION_FORWARD"
        self.state["SAI_FDB_ENTRY_ATTR_PACKET_ACTION"] = data.value()

    @pytest.mark.parametrize(
        "action",
        [
            ("SAI_PACKET_ACTION_DROP"),
            ("SAI_PACKET_ACTION_DONOTDROP"),
            ("SAI_PACKET_ACTION_COPY"),
            ("SAI_PACKET_ACTION_COPY_CANCEL"),
            ("SAI_PACKET_ACTION_TRAP"),
            ("SAI_PACKET_ACTION_LOG"),
            ("SAI_PACKET_ACTION_DENY"),
            ("SAI_PACKET_ACTION_TRANSIT"),
            ("SAI_PACKET_ACTION_FORWARD")
        ]
    )
    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_set_action(self, npu, action):
        attr = "SAI_FDB_ENTRY_ATTR_PACKET_ACTION"
        status = npu.set(TestFdbEntry.key(npu, npu.default_vlan_oid),
                         [attr, action], do_assert=False)
        npu.assert_status_success(status)
        data = npu.get(TestFdbEntry.key(npu, npu.default_vlan_oid), [attr, ""])
        assert data.value() == action

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_no_bridge_port(self, npu):
        npu.set(TestFdbEntry.key(npu, npu.default_vlan_oid), ["SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", "oid:0x0"])

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_remove_dynamic(self, npu):
        npu.remove_fdb(npu.default_vlan_oid, TestFdbEntry.mac)

    @pytest.mark.dependency(depends=['TestFdbEntry::test_create_dynamic'])
    def test_duplicated_remove(self, npu):
        status = npu.remove_fdb(npu.default_vlan_oid, TestFdbEntry.mac, do_assert=False)
        assert status == "SAI_STATUS_ITEM_NOT_FOUND"


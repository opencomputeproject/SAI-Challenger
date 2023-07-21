import pytest
from saichallenger.common.sai_data import SaiObjType
from saichallenger.common.sai import Sai


bridge_attrs = Sai.get_obj_attrs(SaiObjType.BRIDGE)
bport_attrs = Sai.get_obj_attrs(SaiObjType.BRIDGE_PORT)
bport_attrs_default = {}
bport_attrs_updated = {}


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()


@pytest.fixture(scope="module")
def sai_bport_obj(npu):
    bport_oid = npu.dot1q_bp_oids[0]
    yield bport_oid

    # Fall back to the defaults
    for attr in bport_attrs_updated:
        if attr in bport_attrs_default:
            npu.set(bport_oid, [attr, bport_attrs_default[attr]])


class TestDot1qBridge:
    state = dict()

    @pytest.mark.parametrize(
        "attr,attr_type",
        bridge_attrs
    )
    def test_get_attr(self, npu, dataplane, attr, attr_type):
        status, data = npu.get_by_type(npu.dot1q_br_oid, attr, attr_type)
        npu.assert_status_success(status)
        if attr == "SAI_BRIDGE_ATTR_TYPE":
            assert data.value() == "SAI_BRIDGE_TYPE_1Q"
        elif attr == "SAI_BRIDGE_ATTR_MAX_LEARNED_ADDRESSES":
            self.state["SAI_BRIDGE_ATTR_MAX_LEARNED_ADDRESSES"] = data.value()

    @pytest.mark.parametrize(
        "attr,attr_value",
        [
            ("SAI_BRIDGE_ATTR_MAX_LEARNED_ADDRESSES", "0"),
            ("SAI_BRIDGE_ATTR_MAX_LEARNED_ADDRESSES", "128"),
            ("SAI_BRIDGE_ATTR_MAX_LEARNED_ADDRESSES", None),
            ("SAI_BRIDGE_ATTR_LEARN_DISABLE", "true"),
            ("SAI_BRIDGE_ATTR_LEARN_DISABLE", "false"),
            ("SAI_BRIDGE_ATTR_LEARN_DISABLE", None),
        ],
    )
    def test_set_attr(self, npu, dataplane, attr, attr_value):
        if attr_value is None:
            attr_value = self.state.get(attr)
            if attr_value is None:
                pytest.skip("no default value")
        npu.set(npu.dot1q_br_oid, [attr, attr_value])
        assert npu.get(npu.dot1q_br_oid, [attr]).value() == attr_value


class TestDot1dBridge:
    state = dict()

    @pytest.mark.dependency()
    def test_create(self, npu):
        self.state["oid"] = npu.create(SaiObjType.BRIDGE, ["SAI_BRIDGE_ATTR_TYPE", "SAI_BRIDGE_TYPE_1D"])
        assert self.state["oid"] != "oid:0x0"

    @pytest.mark.parametrize(
        "attr,attr_type",
        bridge_attrs
    )
    @pytest.mark.dependency(depends=['TestDot1dBridge::test_create'])
    def test_get_attr(self, npu, dataplane, attr, attr_type):
        status, data = npu.get_by_type(self.state["oid"], attr, attr_type)
        npu.assert_status_success(status)

        if attr == "SAI_BRIDGE_ATTR_TYPE":
            assert data.value() == "SAI_BRIDGE_TYPE_1D"
        elif attr == "SAI_BRIDGE_ATTR_PORT_LIST":
            assert len(data.to_list()) == 0

    @pytest.mark.dependency(depends=['TestDot1dBridge::test_create'])
    def test_remove(self, npu):
        npu.remove(self.state["oid"])


class TestBridgePort:
    @pytest.mark.parametrize(
        "attr,attr_type",
        bport_attrs
    )
    def test_get_before_set_attr(self, npu, dataplane, sai_bport_obj, attr, attr_type):
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
    def test_set_attr(self, npu, dataplane, sai_bport_obj, attr, attr_value):
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
    def test_get_after_set_attr(self, npu, dataplane, sai_bport_obj, attr, attr_type):
        status, data = npu.get_by_type(sai_bport_obj, attr, attr_type, do_assert=False)
        npu.assert_status_success(status)

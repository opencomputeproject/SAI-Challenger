import itertools
import pytest
from saichallenger.common.sai import Sai

switch_attrs = Sai.get_obj_attrs("SAI_OBJECT_TYPE_SWITCH")


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


class TestSwitch:
    state = dict()
    miss_packet_actions_map = tuple(itertools.product(
    (
        "SAI_SWITCH_ATTR_FDB_UNICAST_MISS_PACKET_ACTION",
        "SAI_SWITCH_ATTR_FDB_BROADCAST_MISS_PACKET_ACTION",
        "SAI_SWITCH_ATTR_FDB_MULTICAST_MISS_PACKET_ACTION"
    ),
    (
        "SAI_PACKET_ACTION_DROP",
        "SAI_PACKET_ACTION_DONOTDROP",
        "SAI_PACKET_ACTION_COPY",
        "SAI_PACKET_ACTION_COPY_CANCEL",
        "SAI_PACKET_ACTION_TRAP",
        "SAI_PACKET_ACTION_LOG",
        "SAI_PACKET_ACTION_DENY",
        "SAI_PACKET_ACTION_TRANSIT",
        "SAI_PACKET_ACTION_FORWARD",
        None,
    )))

    @pytest.mark.parametrize(
        "attr,attr_type",
        switch_attrs
    )
    def test_get_attr(self, npu, dataplane, attr, attr_type):
        status, data = npu.get_by_type(npu.switch_oid, attr, attr_type, do_assert = False)
        npu.assert_status_success(status)
        self.state[attr] = data.value()

    @pytest.mark.parametrize(
            "attr,attr_value",
            [
                ("SAI_SWITCH_ATTR_SRC_MAC_ADDRESS", "00:11:22:33:44:55"),
                ("SAI_SWITCH_ATTR_SRC_MAC_ADDRESS", "00:00:00:00:00:00"),
                ("SAI_SWITCH_ATTR_SRC_MAC_ADDRESS", None),
                ("SAI_SWITCH_ATTR_SWITCHING_MODE", "SAI_SWITCH_SWITCHING_MODE_CUT_THROUGH"),
                ("SAI_SWITCH_ATTR_SWITCHING_MODE", "SAI_SWITCH_SWITCHING_MODE_STORE_AND_FORWARD"),
                ("SAI_SWITCH_ATTR_RESTART_WARM", "true"),
                ("SAI_SWITCH_ATTR_RESTART_WARM", "false"),
                ("SAI_SWITCH_ATTR_RESTART_WARM", None),
                ("SAI_SWITCH_ATTR_WARM_RECOVER", "true"),
                ("SAI_SWITCH_ATTR_WARM_RECOVER", "false"),
                ("SAI_SWITCH_ATTR_WARM_RECOVER", None),
                ("SAI_SWITCH_ATTR_COUNTER_REFRESH_INTERVAL", "0"),
                ("SAI_SWITCH_ATTR_COUNTER_REFRESH_INTERVAL", "1"),
                ("SAI_SWITCH_ATTR_SWITCH_SHELL_ENABLE", "true"),
                ("SAI_SWITCH_ATTR_SWITCH_SHELL_ENABLE", "false"),
                ("SAI_SWITCH_ATTR_FAST_API_ENABLE", "true"),
                ("SAI_SWITCH_ATTR_FAST_API_ENABLE", "false"),
                ("SAI_SWITCH_ATTR_MIRROR_TC", "1"),
                ("SAI_SWITCH_ATTR_MIRROR_TC", "255"),
                ("SAI_SWITCH_ATTR_CRC_CHECK_ENABLE", "false"),
                ("SAI_SWITCH_ATTR_CRC_CHECK_ENABLE", "true"),
                ("SAI_SWITCH_ATTR_CRC_RECALCULATION_ENABLE", "false"),
                ("SAI_SWITCH_ATTR_CRC_RECALCULATION_ENABLE", "true"),
                ("SAI_SWITCH_ATTR_MAX_LEARNED_ADDRESSES", "128"),
                ("SAI_SWITCH_ATTR_MAX_LEARNED_ADDRESSES", "0"),
                ("SAI_SWITCH_ATTR_FDB_AGING_TIME", "600"),
                ("SAI_SWITCH_ATTR_FDB_AGING_TIME", "300"),
                ("SAI_SWITCH_ATTR_FDB_AGING_TIME", "0"),
                ("SAI_SWITCH_ATTR_FDB_AGING_TIME", None),
                ("SAI_SWITCH_ATTR_BCAST_CPU_FLOOD_ENABLE", "true"),
                ("SAI_SWITCH_ATTR_BCAST_CPU_FLOOD_ENABLE", "false"),
                ("SAI_SWITCH_ATTR_MCAST_CPU_FLOOD_ENABLE", "true"),
                ("SAI_SWITCH_ATTR_MCAST_CPU_FLOOD_ENABLE", "false"),
                *miss_packet_actions_map,
            ],
        )
    def test_set_attr(self, npu, dataplane, attr, attr_value):
        if attr_value is None:
            attr_value = self.state.get(attr)
            if attr_value is None:
                pytest.skip("No default value for attribute {}".format(attr))
        status = npu.set(npu.switch_oid, [attr, attr_value], False)
        npu.assert_status_success(status)
        assert npu.get(npu.switch_oid, [attr]).value() == attr_value

import pytest
from saichallenger.common.sai_data import SaiObjType


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


@pytest.fixture(scope="class")
def acl_state():
    state = {
        "table_oid" : "oid:0x0",
        "entries"   : [],
    }
    return state


class TestIngressACL:
    @pytest.mark.dependency()
    def test_create_table(self, npu, acl_state):
        attrs = [
            # ACL table generic attributes
            "SAI_ACL_TABLE_GROUP_ATTR_ACL_STAGE", "SAI_ACL_STAGE_INGRESS",
            "SAI_ACL_TABLE_ATTR_ACL_BIND_POINT_TYPE_LIST",
                    "2:SAI_ACL_BIND_POINT_TYPE_PORT,SAI_ACL_BIND_POINT_TYPE_LAG",
            # ACL table fields
            "SAI_ACL_TABLE_ATTR_FIELD_ETHER_TYPE",      "true",
            "SAI_ACL_TABLE_ATTR_FIELD_OUTER_VLAN_ID",   "true",
            "SAI_ACL_TABLE_ATTR_FIELD_ACL_IP_TYPE",     "true",
            "SAI_ACL_TABLE_ATTR_FIELD_SRC_IP",          "true",
            "SAI_ACL_TABLE_ATTR_FIELD_DST_IP",          "true",
            "SAI_ACL_TABLE_ATTR_FIELD_ICMP_TYPE",       "true",
            "SAI_ACL_TABLE_ATTR_FIELD_ICMP_CODE",       "true",
            "SAI_ACL_TABLE_ATTR_FIELD_IP_PROTOCOL",     "true",
            "SAI_ACL_TABLE_ATTR_FIELD_L4_SRC_PORT",     "true",
            "SAI_ACL_TABLE_ATTR_FIELD_L4_DST_PORT",     "true",
            "SAI_ACL_TABLE_ATTR_FIELD_TCP_FLAGS",       "true",
            "SAI_ACL_TABLE_ATTR_FIELD_ACL_RANGE_TYPE",
                    "2:SAI_ACL_RANGE_TYPE_L4_DST_PORT_RANGE,SAI_ACL_RANGE_TYPE_L4_SRC_PORT_RANGE",
        ]
        acl_state["table_oid"] = npu.create(SaiObjType.ACL_TABLE, attrs)
        assert acl_state["table_oid"] != "oid:0x0"


    @pytest.mark.parametrize(
        "match,action,priority",
        [
            (
                [["SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE",        "2048",     "0xffff"]],
                "SAI_PACKET_ACTION_DROP",       "1"
            ),
            (
                [["SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP",            "20.0.0.2", "255.255.255.255"]],
                "SAI_PACKET_ACTION_FORWARD",    "9990"
            ),
            (
                [
                    ["SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE",     "2048",     "0xffff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP",         "20.0.0.4", "255.255.255.255"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL",    "1",        "0xff"],
                ],
                "SAI_PACKET_ACTION_FORWARD",    "9988"
            ),
            (
                [
                    ["SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE",     "2048",     "0xffff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP",         "20.0.0.4", "255.255.255.255"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL",    "17",       "0xff"],
                ],
                "SAI_PACKET_ACTION_FORWARD",    "9987"
            ),
            (
                [
                    ["SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE",     "2048",         "0xffff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_DST_IP",         "192.168.0.8",  "255.255.255.255"],
                ],
                "SAI_PACKET_ACTION_DROP",       "9985"
            ),
            (
                [
                    ["SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE",     "2048",     "0xffff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_SRC_IPV6",       "2000::1",  "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL",    "17",       "0xff"],
                ],
                "SAI_PACKET_ACTION_FORWARD",    "9987"
            ),
            (
                [
                    ["SAI_ACL_ENTRY_ATTR_FIELD_DST_MAC",        "00:26:dd:14:c4:ee", "ff:ff:ff:ff:ff:ff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE",     "2048",     "0xffff"],
                    ["SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL",    "17",       "0xff"],
                ],
                "SAI_PACKET_ACTION_FORWARD",    "9987"
            ),
        ]
    )
    @pytest.mark.dependency(depends=['TestIngressACL::test_create_table'])
    def test_create_entry(self, npu, acl_state, match, action, priority):
        # Create ACL counter
        counter_attrs = [
            "SAI_ACL_COUNTER_ATTR_TABLE_ID",            acl_state["table_oid"],
            "SAI_ACL_COUNTER_ATTR_ENABLE_BYTE_COUNT",   "true",
            "SAI_ACL_COUNTER_ATTR_ENABLE_PACKET_COUNT", "true",
        ]
        counter_oid = npu.create(SaiObjType.ACL_COUNTER, counter_attrs)

        # Create ACL entry
        entry_attrs = [
            "SAI_ACL_ENTRY_ATTR_TABLE_ID",              acl_state["table_oid"],
            "SAI_ACL_ENTRY_ATTR_PRIORITY",              priority,
            "SAI_ACL_ENTRY_ATTR_ADMIN_STATE",           "true",
            "SAI_ACL_ENTRY_ATTR_ACTION_PACKET_ACTION",  action,
        ]
        for field in match:
            if field[0] == "SAI_ACL_ENTRY_ATTR_FIELD_ACL_RANGE_TYPE":
                # TODO: Create SaiObjType.ACL_RANGE object, append field to @entry_attrs
                continue
            else:
                entry_attrs.append(field[0])
                entry_attrs.append(field[1] + "&mask:" + field[2])

        # Add ACL entry action counter
        entry_attrs.append("SAI_ACL_ENTRY_ATTR_ACTION_COUNTER")
        entry_attrs.append(counter_oid)

        status, entry_oid = npu.create(SaiObjType.ACL_ENTRY, entry_attrs, do_assert=False)
        if status != "SAI_STATUS_SUCCESS":
            npu.remove(counter_oid)
        assert status == "SAI_STATUS_SUCCESS"

        # Cache OIDs
        acl_state["entries"].append(entry_oid)
        acl_state["entries"].append(counter_oid)


    @pytest.mark.dependency(depends=['TestIngressACL::test_create_table'])
    def test_remove_entries(self, npu, acl_state):
        if len(acl_state["entries"]) == 0:
            pytest.skip("no ACL entries to remove")
        for oid in acl_state["entries"]:
            npu.remove(oid)


    @pytest.mark.dependency(depends=['TestIngressACL::test_create_table'])
    def test_remove_table(self, npu, acl_state):
        assert acl_state["table_oid"] != "oid:0x0"
        npu.remove(acl_state["table_oid"])

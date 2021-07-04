import pytest
from sai import SaiObjType

port_attrs = [
    ("SAI_PORT_ATTR_TYPE",                                      "sai_port_type_t"),
    ("SAI_PORT_ATTR_OPER_STATUS",                               "sai_port_oper_status_t"),
    ("SAI_PORT_ATTR_SUPPORTED_BREAKOUT_MODE_TYPE",              "sai_s32_list_t"),
    ("SAI_PORT_ATTR_CURRENT_BREAKOUT_MODE_TYPE",                "sai_port_breakout_mode_type_t"),
    ("SAI_PORT_ATTR_QOS_NUMBER_OF_QUEUES",                      "sai_uint32_t"),
    ("SAI_PORT_ATTR_QOS_QUEUE_LIST",                            "sai_object_list_t"),
    ("SAI_PORT_ATTR_QOS_NUMBER_OF_SCHEDULER_GROUPS",            "sai_uint32_t"),
    ("SAI_PORT_ATTR_QOS_SCHEDULER_GROUP_LIST",                  "sai_object_list_t"),
    ("SAI_PORT_ATTR_QOS_MAXIMUM_HEADROOM_SIZE",                 "sai_uint32_t"),
    ("SAI_PORT_ATTR_SUPPORTED_SPEED",                           "sai_u32_list_t"),
    ("SAI_PORT_ATTR_SUPPORTED_FEC_MODE",                        "sai_s32_list_t"),
    ("SAI_PORT_ATTR_SUPPORTED_HALF_DUPLEX_SPEED",               "sai_u32_list_t"),
    ("SAI_PORT_ATTR_SUPPORTED_AUTO_NEG_MODE",                   "bool"),
    ("SAI_PORT_ATTR_SUPPORTED_FLOW_CONTROL_MODE",               "sai_port_flow_control_mode_t"),
    ("SAI_PORT_ATTR_SUPPORTED_ASYMMETRIC_PAUSE_MODE",           "bool"),
    ("SAI_PORT_ATTR_SUPPORTED_MEDIA_TYPE",                      "sai_port_media_type_t"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_SPEED",                   "sai_u32_list_t"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_FEC_MODE",                "sai_s32_list_t"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_HALF_DUPLEX_SPEED",       "sai_u32_list_t"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_AUTO_NEG_MODE",           "bool"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_FLOW_CONTROL_MODE",       "sai_port_flow_control_mode_t"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_ASYMMETRIC_PAUSE_MODE",   "bool"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_MEDIA_TYPE",              "sai_port_media_type_t"),
    ("SAI_PORT_ATTR_REMOTE_ADVERTISED_OUI_CODE",                "sai_uint32_t"),
    ("SAI_PORT_ATTR_NUMBER_OF_INGRESS_PRIORITY_GROUPS",         "sai_uint32_t"),
    ("SAI_PORT_ATTR_INGRESS_PRIORITY_GROUP_LIST",               "sai_object_list_t"),
    # TODO: Check how to map this into the list
    #("SAI_PORT_ATTR_EYE_VALUES",                                "sai_port_eye_values_list_t"),
    ("SAI_PORT_ATTR_OPER_SPEED",                                "sai_uint32_t"),
    ("SAI_PORT_ATTR_HW_LANE_LIST",                              "sai_u32_list_t"),
    ("SAI_PORT_ATTR_SPEED",                                     "sai_uint32_t"),
    ("SAI_PORT_ATTR_FULL_DUPLEX_MODE",                          "bool"),
    ("SAI_PORT_ATTR_AUTO_NEG_MODE",                             "bool"),
    ("SAI_PORT_ATTR_ADMIN_STATE",                               "bool"),
    ("SAI_PORT_ATTR_MEDIA_TYPE",                                "sai_port_media_type_t"),
    ("SAI_PORT_ATTR_ADVERTISED_SPEED",                          "sai_u32_list_t"),
    ("SAI_PORT_ATTR_ADVERTISED_FEC_MODE",                       "sai_s32_list_t"),
    ("SAI_PORT_ATTR_ADVERTISED_HALF_DUPLEX_SPEED",              "sai_u32_list_t"),
    ("SAI_PORT_ATTR_ADVERTISED_AUTO_NEG_MODE",                  "bool"),
    ("SAI_PORT_ATTR_ADVERTISED_FLOW_CONTROL_MODE",              "sai_port_flow_control_mode_t"),
    ("SAI_PORT_ATTR_ADVERTISED_ASYMMETRIC_PAUSE_MODE",          "bool"),
    ("SAI_PORT_ATTR_ADVERTISED_MEDIA_TYPE",                     "sai_port_media_type_t"),
    ("SAI_PORT_ATTR_ADVERTISED_OUI_CODE",                       "sai_uint32_t"),
    ("SAI_PORT_ATTR_PORT_VLAN_ID",                              "sai_uint16_t"),
    ("SAI_PORT_ATTR_DEFAULT_VLAN_PRIORITY",                     "sai_uint8_t"),
    ("SAI_PORT_ATTR_DROP_UNTAGGED",                             "bool"),
    ("SAI_PORT_ATTR_DROP_TAGGED",                               "bool"),
    ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",                    "sai_port_internal_loopback_mode_t"),
    ("SAI_PORT_ATTR_FEC_MODE",                                  "sai_port_fec_mode_t"),
    ("SAI_PORT_ATTR_UPDATE_DSCP",                               "bool"),
    ("SAI_PORT_ATTR_MTU",                                       "sai_uint32_t"),
    ("SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID",            "sai_object_id_t"),
    ("SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID",        "sai_object_id_t"),
    ("SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID",        "sai_object_id_t"),
    ("SAI_PORT_ATTR_GLOBAL_FLOW_CONTROL_MODE",                  "sai_port_flow_control_mode_t"),
    ("SAI_PORT_ATTR_INGRESS_ACL",                               "sai_object_id_t"),
    ("SAI_PORT_ATTR_EGRESS_ACL",                                "sai_object_id_t"),
    ("SAI_PORT_ATTR_INGRESS_MACSEC_ACL",                        "sai_object_id_t"),
    ("SAI_PORT_ATTR_EGRESS_MACSEC_ACL",                         "sai_object_id_t"),
    ("SAI_PORT_ATTR_MACSEC_PORT_LIST",                          "sai_object_list_t"),
    ("SAI_PORT_ATTR_INGRESS_MIRROR_SESSION",                    "sai_object_list_t"),
    ("SAI_PORT_ATTR_EGRESS_MIRROR_SESSION",                     "sai_object_list_t"),
    ("SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE",               "sai_object_id_t"),
    ("SAI_PORT_ATTR_EGRESS_SAMPLEPACKET_ENABLE",                "sai_object_id_t"),
    ("SAI_PORT_ATTR_INGRESS_SAMPLE_MIRROR_SESSION",             "sai_object_list_t"),
    ("SAI_PORT_ATTR_EGRESS_SAMPLE_MIRROR_SESSION",              "sai_object_list_t"),
    ("SAI_PORT_ATTR_POLICER_ID",                                "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_DEFAULT_TC",                            "sai_uint8_t"),
    ("SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP",                       "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_DOT1P_TO_COLOR_MAP",                    "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP",                        "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_DSCP_TO_COLOR_MAP",                     "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP",                       "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DOT1P_MAP",             "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP",              "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP",              "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP",    "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP",             "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID",                  "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST",           "sai_object_list_t"),
    ("SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST",            "sai_object_list_t"),
    ("SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL_MODE",                "sai_port_priority_flow_control_mode_t"),
    ("SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL",                     "sai_uint8_t"),
    ("SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL_RX",                  "sai_uint8_t"),
    ("SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL_TX",                  "sai_uint8_t"),
    ("SAI_PORT_ATTR_META_DATA",                                 "sai_uint32_t"),
    ("SAI_PORT_ATTR_EGRESS_BLOCK_PORT_LIST",                    "sai_object_list_t"),
    ("SAI_PORT_ATTR_HW_PROFILE_ID",                             "sai_uint64_t"),
    ("SAI_PORT_ATTR_EEE_ENABLE",                                "bool"),
    ("SAI_PORT_ATTR_EEE_IDLE_TIME",                             "sai_uint16_t"),
    ("SAI_PORT_ATTR_EEE_WAKE_TIME",                             "sai_uint16_t"),
    ("SAI_PORT_ATTR_PORT_POOL_LIST",                            "sai_object_list_t"),
    ("SAI_PORT_ATTR_ISOLATION_GROUP",                           "sai_object_id_t"),
    ("SAI_PORT_ATTR_PKT_TX_ENABLE",                             "bool"),
    ("SAI_PORT_ATTR_TAM_OBJECT",                                "sai_object_list_t"),
    ("SAI_PORT_ATTR_SERDES_PREEMPHASIS",                        "sai_u32_list_t"),
    ("SAI_PORT_ATTR_SERDES_IDRIVER",                            "sai_u32_list_t"),
    ("SAI_PORT_ATTR_SERDES_IPREDRIVER",                         "sai_u32_list_t"),
    ("SAI_PORT_ATTR_LINK_TRAINING_ENABLE",                      "bool"),
    ("SAI_PORT_ATTR_PTP_MODE",                                  "sai_port_ptp_mode_t"),
    ("SAI_PORT_ATTR_INTERFACE_TYPE",                            "sai_port_interface_type_t"),
    ("SAI_PORT_ATTR_ADVERTISED_INTERFACE_TYPE",                 "sai_s32_list_t"),
    ("SAI_PORT_ATTR_REFERENCE_CLOCK",                           "sai_uint64_t"),
    ("SAI_PORT_ATTR_PRBS_POLYNOMIAL",                           "sai_uint32_t"),
    ("SAI_PORT_ATTR_PORT_SERDES_ID",                            "sai_object_id_t"),
    ("SAI_PORT_ATTR_LINK_TRAINING_FAILURE_STATUS",              "sai_port_link_training_failure_status_t"),
    ("SAI_PORT_ATTR_LINK_TRAINING_RX_STATUS",                   "sai_port_link_training_rx_status_t"),
    ("SAI_PORT_ATTR_PRBS_CONFIG",                               "sai_port_prbs_config_t"),
    ("SAI_PORT_ATTR_PRBS_LOCK_STATUS",                          "bool"),
    ("SAI_PORT_ATTR_PRBS_LOCK_LOSS_STATUS",                     "bool"),
    ("SAI_PORT_ATTR_PRBS_RX_STATUS",                            "sai_port_prbs_rx_status_t"),
    # TODO: Check how to map this into the struct
    #("SAI_PORT_ATTR_PRBS_RX_STATE",                             "sai_prbs_rx_state_t"),
    ("SAI_PORT_ATTR_AUTO_NEG_STATUS",                           "bool"),
    ("SAI_PORT_ATTR_DISABLE_DECREMENT_TTL",                     "bool"),
    ("SAI_PORT_ATTR_QOS_MPLS_EXP_TO_TC_MAP",                    "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_MPLS_EXP_TO_COLOR_MAP",                 "sai_object_id_t"),
    ("SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_MPLS_EXP_MAP",          "sai_object_id_t"),
    ("SAI_PORT_ATTR_TPID",                                      "sai_uint16_t"),
    # TODO: Check how to map this into the list
    #("SAI_PORT_ATTR_ERR_STATUS_LIST",                           "sai_port_err_status_list_t"),
    ("SAI_PORT_ATTR_FABRIC_ATTACHED",                           "bool"),
    ("SAI_PORT_ATTR_FABRIC_ATTACHED_SWITCH_TYPE",               "sai_switch_type_t"),
    ("SAI_PORT_ATTR_FABRIC_ATTACHED_SWITCH_ID",                 "sai_uint32_t"),
    ("SAI_PORT_ATTR_FABRIC_ATTACHED_PORT_INDEX",                "sai_uint32_t"),
    # TODO: Check how to map this into the struct
    #("SAI_PORT_ATTR_FABRIC_REACHABILITY",                       "sai_fabric_port_reachability_t"),
    ("SAI_PORT_ATTR_SYSTEM_PORT",                               "sai_object_id_t"),

]

port_attrs_default = {}
port_attrs_updated = {}


@pytest.fixture(scope="module")
def sai_port_obj(npu):
    port_oid = npu.port_oids[0]
    yield port_oid

    # Fall back to the defaults
    for attr in port_attrs_updated:
        if attr in port_attrs_default:
            npu.set(port_oid, [attr, port_attrs_default[attr]])


@pytest.mark.parametrize(
    "attr,attr_type",
    port_attrs
)
def test_get_before_set_attr(npu, dataplane, sai_port_obj, attr, attr_type):#, attr_val):
    status, data = npu.get_by_type(sai_port_obj, attr, attr_type, do_assert = False)

    if status == "SAI_STATUS_NOT_SUPPORTED" or status == "SAI_STATUS_ATTR_NOT_SUPPORTED_0":
        pytest.skip("not supported")

    if status == "SAI_STATUS_NOT_IMPLEMENTED" or status == "SAI_STATUS_ATTR_NOT_IMPLEMENTED_0":
        pytest.skip("not implemented")

    assert status == "SAI_STATUS_SUCCESS"

    if status == "SAI_STATUS_SUCCESS":
        port_attrs_default[attr] = data.value()

    #assert data.value() == attr_val


@pytest.mark.parametrize(
    "attr,attr_value",
    [
        ("SAI_PORT_ATTR_ADMIN_STATE",               "true"),
        ("SAI_PORT_ATTR_ADMIN_STATE",               "false"),
        ("SAI_PORT_ATTR_PORT_VLAN_ID",              "100"),
        ("SAI_PORT_ATTR_DEFAULT_VLAN_PRIORITY",     "3"),
        ("SAI_PORT_ATTR_DROP_UNTAGGED",             "true"),
        ("SAI_PORT_ATTR_DROP_UNTAGGED",             "false"),
        ("SAI_PORT_ATTR_DROP_TAGGED",               "true"),
        ("SAI_PORT_ATTR_DROP_TAGGED",               "false"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "SAI_PORT_INTERNAL_LOOPBACK_MODE_PHY"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "SAI_PORT_INTERNAL_LOOPBACK_MODE_NONE"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "SAI_PORT_INTERNAL_LOOPBACK_MODE_MAC"),
        ("SAI_PORT_ATTR_UPDATE_DSCP",               "true"),
        ("SAI_PORT_ATTR_UPDATE_DSCP",               "false"),
        ("SAI_PORT_ATTR_MTU",                       "9000"),
        ("SAI_PORT_ATTR_TPID",                      "37120"),   # TPID=0x9100
    ],
)
def test_set_attr(npu, dataplane, sai_port_obj, attr, attr_value):
    status = npu.set(sai_port_obj, [attr, attr_value], False)

    if status == "SAI_STATUS_NOT_SUPPORTED" or status == "SAI_STATUS_ATTR_NOT_SUPPORTED_0":
        pytest.skip("not supported")

    if status == "SAI_STATUS_NOT_IMPLEMENTED" or status == "SAI_STATUS_ATTR_NOT_IMPLEMENTED_0":
        pytest.skip("not implemented")

    assert status == "SAI_STATUS_SUCCESS"

    if status == "SAI_STATUS_SUCCESS":
        port_attrs_updated[attr] = attr_value


@pytest.mark.parametrize(
    "attr,attr_type",
    [
        ("SAI_PORT_ATTR_ADMIN_STATE",               "bool"),
        ("SAI_PORT_ATTR_PORT_VLAN_ID",              "sai_uint16_t"),
        ("SAI_PORT_ATTR_DEFAULT_VLAN_PRIORITY",     "sai_uint8_t"),
        ("SAI_PORT_ATTR_DROP_UNTAGGED",             "bool"),
        ("SAI_PORT_ATTR_DROP_TAGGED",               "bool"),
        ("SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE",    "sai_port_internal_loopback_mode_t"),
        ("SAI_PORT_ATTR_UPDATE_DSCP",               "bool"),
        ("SAI_PORT_ATTR_MTU",                       "sai_uint32_t"),
        ("SAI_PORT_ATTR_TPID",                      "sai_uint16_t"),
    ]
)
def test_get_after_set_attr(npu, dataplane, sai_port_obj, attr, attr_type):
    status, data = npu.get_by_type(sai_port_obj, attr, attr_type, do_assert = False)

    if status == "SAI_STATUS_NOT_SUPPORTED" or status == "SAI_STATUS_ATTR_NOT_SUPPORTED_0":
        pytest.skip("not supported")

    if status == "SAI_STATUS_NOT_IMPLEMENTED" or status == "SAI_STATUS_ATTR_NOT_IMPLEMENTED_0":
        pytest.skip("not implemented")

    assert status == "SAI_STATUS_SUCCESS"

    if attr in port_attrs_updated:
        assert data.value() == port_attrs_updated[attr]

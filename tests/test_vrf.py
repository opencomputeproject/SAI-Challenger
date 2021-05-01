import pytest
from common.switch import Sai, SaiObjType
import json

from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_no_packet_any


def test_default_vrf(sai, dataplane):
    # Get default VRF
    data = sai.get(sai.sw_oid,
                   ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).to_json()
    assert data[0] == 'SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID'
    vrf_oid = data[1]
    assert vrf_oid != 'oid:0x0'

    # Set/Get one VRF attribute
    sai.set(vrf_oid, ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true"])

    admin_v4_state = sai.get(vrf_oid, ["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true"]).to_json()
    assert admin_v4_state[1] == 'true'

    # Get multiple VRF attributes
    if not sai.libsaivs:
        # TODO: Not implemented for SONiC VS for the attributes that were not set before
        attrs = sai.get(vrf_oid,
                        [
                            "SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true",
                            "SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true",
                            "SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS", "00:00:00:00:00:00",
                            "SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                            "SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                            "SAI_VIRTUAL_ROUTER_ATTR_LABEL", ""
                        ]).to_json()

    # Remove default VRF should cause SAI_STATUS_OBJECT_IN_USE
    if not sai.libsaivs:
        # TODO: Not implemented for SONiC VS
        status = sai.remove(vrf_oid, False)
        assert (status == 'SAI_STATUS_OBJECT_IN_USE')


def test_rif_create_remove(sai, dataplane):
    # Create VRFs
    vrf_oid1 = sai.create(SaiObjType.VIRTUAL_ROUTER, [])
    vrf_oid2 = sai.create(SaiObjType.VIRTUAL_ROUTER, [])

    # Remove ports
    for oid in sai.sw.dot1q_bp_oids[0:3]:
        sai.remove_vlan_member(sai.sw.default_vlan_oid, oid)
        sai.remove(oid)

    # Create RIF1
    rif_oid1 = sai.create(SaiObjType.ROUTER_INTERFACE,
                          [
                              'SAI_ROUTER_INTERFACE_ATTR_TYPE', 'SAI_ROUTER_INTERFACE_TYPE_PORT',
                              'SAI_ROUTER_INTERFACE_ATTR_PORT_ID', sai.sw.port_oids[0],
                              'SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID', vrf_oid1,
                          ])

    # Create LAG1
    lag_oid = sai.create(SaiObjType.LAG, [])

    # Create LAG1 members
    lag_mbr_oids = []
    for oid in sai.sw.port_oids[1:3]:
        lag_mbr = sai.create(SaiObjType.LAG_MEMBER,
                             [
                                 "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                                 "SAI_LAG_MEMBER_ATTR_PORT_ID", oid
                             ])
        lag_mbr_oids.append(lag_mbr)

    # Create RIF2
    rif_oid2 = sai.create(SaiObjType.ROUTER_INTERFACE,
                          [
                              'SAI_ROUTER_INTERFACE_ATTR_TYPE', 'SAI_ROUTER_INTERFACE_TYPE_PORT',
                              'SAI_ROUTER_INTERFACE_ATTR_PORT_ID', lag_oid,
                              'SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID', vrf_oid2,
                          ])

    # Delete RIFs
    sai.remove(rif_oid1)
    sai.remove(rif_oid2)

    # Delete LAG1 members
    for oid in lag_mbr_oids:
        sai.remove(oid)

    # Delete LAG1
    sai.remove(lag_oid)

    # Delete VRFs
    sai.remove(vrf_oid1)
    sai.remove(vrf_oid2)

    # Create bridge port for ports removed from LAG
    for idx, oid in enumerate(sai.sw.port_oids[0:3]):
        bp_oid = sai.create(SaiObjType.BRIDGE_PORT,
                            [
                                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                "SAI_BRIDGE_PORT_ATTR_PORT_ID", oid,
                                # "SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", dot1q_br.oid(),
                                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                            ])
        sai.sw.dot1q_bp_oids[idx] = bp_oid

    # Add ports to default VLAN and set PVID
    for idx, oid in enumerate(sai.sw.port_oids[0:3]):
        sai.create_vlan_member(sai.sw.default_vlan_oid, sai.sw.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        sai.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", sai.sw.default_vlan_id])

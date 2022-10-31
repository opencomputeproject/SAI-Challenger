import pytest
from sai_data import SaiObjType
import json

from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_no_packet_any


def test_default_vrf(npu, dataplane):
    # Get default VRF
    data = npu.get(oid=npu.switch_oid,
                   attrs=["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).to_json()
    assert data[0] == 'SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID'
    vrf_oid = data[1]
    assert vrf_oid != 'oid:0x0'

    # Set/Get one VRF attribute
    npu.set(oid=vrf_oid, attr=["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true"])

    admin_v4_state = npu.get(oid=vrf_oid, attrs=["SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true"]).to_json()
    assert admin_v4_state[1] == 'true'

    # Get multiple VRF attributes
    if not npu.libsaivs:
        # TODO: Not implemented for SONiC VS for the attributes that were not set before
        attrs = npu.get(oid=vrf_oid,
                        attrs=[
                            "SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE", "true",
                            "SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE", "true",
                            "SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS", "00:00:00:00:00:00",
                            "SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                            "SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION", "SAI_PACKET_ACTION_TRAP",
                            "SAI_VIRTUAL_ROUTER_ATTR_LABEL", ""
                        ]).to_json()

    # Remove default VRF should cause SAI_STATUS_OBJECT_IN_USE
    if not npu.libsaivs:
        # TODO: Not implemented for SONiC VS
        status = npu.remove(vrf_oid, False)
        assert (status == 'SAI_STATUS_OBJECT_IN_USE')


def test_rif_create_remove(npu, dataplane):
    # Create VRFs
    vrf_oid1 = npu.create(obj_type=SaiObjType.VIRTUAL_ROUTER, attrs=[])
    vrf_oid2 = npu.create(obj_type=SaiObjType.VIRTUAL_ROUTER, attrs=[])

    # Remove ports
    for oid in npu.dot1q_bp_oids[0:3]:
        npu.remove_vlan_member(npu.default_vlan_oid, oid)
        npu.remove(oid=oid)

    # Create RIF1
    rif_oid1 = npu.create(obj_type=SaiObjType.ROUTER_INTERFACE,
                          attrs=[
                              'SAI_ROUTER_INTERFACE_ATTR_TYPE', 'SAI_ROUTER_INTERFACE_TYPE_PORT',
                              'SAI_ROUTER_INTERFACE_ATTR_PORT_ID', npu.port_oids[0],
                              'SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID', vrf_oid1,
                          ])

    # Create LAG1
    lag_oid = npu.create(obj_type=SaiObjType.LAG, attrs=[])

    # Create LAG1 members
    lag_mbr_oids = []
    for oid in npu.port_oids[1:3]:
        lag_mbr = npu.create(obj_type=SaiObjType.LAG_MEMBER,
                             attrs=[
                                 "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                                 "SAI_LAG_MEMBER_ATTR_PORT_ID", oid
                             ])
        lag_mbr_oids.append(lag_mbr)

    # Create RIF2
    rif_oid2 = npu.create(obj_type=SaiObjType.ROUTER_INTERFACE,
                          attrs=[
                              'SAI_ROUTER_INTERFACE_ATTR_TYPE', 'SAI_ROUTER_INTERFACE_TYPE_PORT',
                              'SAI_ROUTER_INTERFACE_ATTR_PORT_ID', lag_oid,
                              'SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID', vrf_oid2,
                          ])

    # Delete RIFs
    npu.remove(oid=rif_oid1)
    npu.remove(oid=rif_oid2)

    # Delete LAG1 members
    for oid in lag_mbr_oids:
        npu.remove(oid=oid)

    # Delete LAG1
    npu.remove(oid=lag_oid)

    # Delete VRFs
    npu.remove(oid=vrf_oid1)
    npu.remove(oid=vrf_oid2)

    # Create bridge port for ports removed from LAG
    for idx, oid in enumerate(npu.port_oids[0:3]):
        bp_oid = npu.create(obj_type=SaiObjType.BRIDGE_PORT,
                            attrs=[
                                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                "SAI_BRIDGE_PORT_ATTR_PORT_ID", oid,
                                # "SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", dot1q_br.oid(),
                                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                            ])
        npu.dot1q_bp_oids[idx] = bp_oid

    # Add ports to default VLAN and set PVID
    for idx, oid in enumerate(npu.port_oids[0:3]):
        npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(oid=oid, attr=["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

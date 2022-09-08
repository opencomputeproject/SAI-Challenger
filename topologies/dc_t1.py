from contextlib import contextmanager
import pytest
from sai_data import SaiObjType


@contextmanager
def config(npu):
    topo_cfg = {
        "lo_rif_oid": None,
        "cpu_port_oid": None,
    }

    # Create Loopback RIF
    lo_rif_oid = npu.create(SaiObjType.ROUTER_INTERFACE,
                            [
                                "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", npu.default_vrf_oid,
                                "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_LOOPBACK",
                                "SAI_ROUTER_INTERFACE_ATTR_MTU", "9100"
                            ])
    topo_cfg["lo_rif_oid"] = lo_rif_oid

    # Get CPU port
    cpu_port_oid = npu.get(npu.oid, ["SAI_SWITCH_ATTR_CPU_PORT", "oid:0x0"]).oid()
    topo_cfg["cpu_port_oid"] = cpu_port_oid

    # Get port HW lanes
    for oid in npu.port_oids:
        port_lanes = npu.get(oid, ["SAI_PORT_ATTR_HW_LANE_LIST", "8:0,0,0,0,0,0,0,0"]).to_list()

    # Remove default VLAN members
    vlan_mbr_oids = npu.get_list(npu.default_vlan_oid, "SAI_VLAN_ATTR_MEMBER_LIST", "oid:0x0")
    for oid in vlan_mbr_oids:
        npu.remove(oid)

    # Remove default 1Q bridge members
    dot1q_mbr_oids = npu.get_list(npu.dot1q_br_oid, "SAI_BRIDGE_ATTR_PORT_LIST", "oid:0x0")
    for oid in dot1q_mbr_oids:
        bp_type = npu.get(oid, ["SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT"]).value()
        if bp_type == "SAI_BRIDGE_PORT_TYPE_PORT":
            npu.remove(oid)
    npu.dot1q_bp_oids.clear()

    # Create default routes
    npu.create_route("0.0.0.0/0", npu.default_vrf_oid, None,
                     ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"])
    npu.create_route("::/0", npu.default_vrf_oid, None,
                     ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"])

    # Create Loopback RIF routes
    npu.create_route("fe80::5054:ff:fe12:3456/128", npu.default_vrf_oid, cpu_port_oid,
                     ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])
    npu.create_route("fe80::/10", npu.default_vrf_oid, cpu_port_oid,
                     ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])

    yield topo_cfg
    
    # TODO: TEARDOWN

    # Remove default routes
    npu.remove_route("fe80::/10", npu.default_vrf_oid)
    npu.remove_route("fe80::5054:ff:fe12:3456/128", npu.default_vrf_oid)
    npu.remove_route("::/0", npu.default_vrf_oid)
    npu.remove_route("0.0.0.0/0", npu.default_vrf_oid)

    # Create default 1Q bridge members
    for oid in npu.port_oids:
        bp_oid = npu.create(SaiObjType.BRIDGE_PORT,
                            [
                                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                "SAI_BRIDGE_PORT_ATTR_PORT_ID", oid,
                                # "SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", dot1q_br.oid(),
                                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                            ])
        npu.dot1q_bp_oids.append(bp_oid)

    # Create default VLAN members and set PVID
    for idx, oid in enumerate(npu.port_oids):
        npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(oid, ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

    # Remove Loopback RIF
    npu.remove(lo_rif_oid)


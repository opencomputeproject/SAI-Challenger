import pytest
from ptf.testutils import simple_tcp_packet, send_packet, verify_packets

@pytest.fixture(scope="module", autouse=True)
def discovery(npu):
     npu.objects_discovery()

def test_l2_trunk_to_trunk_vlan_dd(npu, dataplane):
    """
    Description:
    Check trunk to trunk VLAN members forwarding

    #1. Create a VLAN 10
    #2. Add two ports as tagged members to the VLAN
    #3. Setup static FDB entries for port 1 and port 2
    #4. Send a simple vlan tag (10) packet on port 1 and verify packet on port 2
    #5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    cmds = [{
        "name": "vlan_10",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_VLAN",
        "attributes": [
            "SAI_VLAN_ATTR_VLAN_ID", vlan_id
        ]
    }]

    for idx, mac in enumerate(macs):
        cmds.append({
            "name": f"vlan_member_{idx}",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_VLAN_MEMBER",
            "attributes": [
                "SAI_VLAN_MEMBER_ATTR_VLAN_ID", "$vlan_10",
                "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", f"$BRIDGE_PORT_{idx}",
                "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", "SAI_VLAN_TAGGING_MODE_TAGGED"
            ]
        })
        cmds.append({
            "name": f"fdb_{idx}",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_FDB_ENTRY",
            "key": {
                "bv_id": "$vlan_10",
                "mac_address": mac,
                "switch_id" : "$SWITCH_ID"
            },
            "attributes": [
                "SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_STATIC",
                "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", f"$BRIDGE_PORT_{idx}",
                "SAI_FDB_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"
            ]
        })
    status = [*npu.process_commands(cmds)]
    try:
        if npu.run_traffic:
            pkt = simple_tcp_packet(eth_dst=macs[1],
                                    eth_src=macs[0],
                                    dl_vlan_enable=True,
                                    vlan_vid=10,
                                    ip_dst='10.0.0.1',
                                    ip_id=101,
                                    ip_ttl=64)

            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, pkt, [1])
    finally:
        status = [*npu.process_commands(cmds, cleanup=True)]

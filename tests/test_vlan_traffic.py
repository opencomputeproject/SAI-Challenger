import pytest
from pprint import pprint


@pytest.fixture(scope="module", autouse=True)
def discovery(npu):
    npu.objects_discovery()


def test_l2_trunk_to_trunk_vlan_dd(npu):
    vlan_id = "10"

    '''
    CLI: sudo config vlan add 10
    SAI:
    |c|SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP
    2022-09-04.12:17:08.409539|c|SAI_OBJECT_TYPE_VLAN:oid:0x26000000000622|SAI_VLAN_ATTR_VLAN_ID=10
    2022-09-04.12:17:08.416163|S|SAI_OBJECT_TYPE_ROUTE_ENTRY||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0

    CLI: sudo config vlan member add -u 10 Ethernet120
    SAI
    Adding vlan member -----------
    2022-09-04.12:17:51.643262|c|SAI_OBJECT_TYPE_BRIDGE_PORT:oid:0x3a000000000623|SAI_BRIDGE_PORT_ATTR_TYPE=SAI_BRIDGE_PORT_TYPE_PORT|SAI_BRIDGE_PORT_ATTR_PORT_ID=oid:0x1000000000004|SAI_BRIDGE_PORT_ATTR_ADMIN_STATE=true|SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE=SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW
    2022-09-04.12:17:51.645928|s|SAI_OBJECT_TYPE_HOSTIF:oid:0xd0000000005b2|SAI_HOSTIF_ATTR_VLAN_TAG=SAI_HOSTIF_VLAN_TAG_KEEP
    2022-09-04.12:17:51.648374|c|SAI_OBJECT_TYPE_VLAN_MEMBER:oid:0x27000000000624|SAI_VLAN_MEMBER_ATTR_VLAN_ID=oid:0x26000000000622|SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID=oid:0x3a000000000623|SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE=SAI_VLAN_TAGGING_MODE_UNTAGGED
    2022-09-04.12:17:51.651184|s|SAI_OBJECT_TYPE_PORT:oid:0x1000000000004|SAI_PORT_ATTR_PORT_VLAN_ID=10


    CLI: sudo config vlan member add -u 10 Ethernet124
    SAI:
    2022-09-04.12:18:27.699269|c|SAI_OBJECT_TYPE_BRIDGE_PORT:oid:0x3a000000000625|SAI_BRIDGE_PORT_ATTR_TYPE=SAI_BRIDGE_PORT_TYPE_PORT|SAI_BRIDGE_PORT_ATTR_PORT_ID=oid:0x1000000000005|SAI_BRIDGE_PORT_ATTR_ADMIN_STATE=true|SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE=SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW
    2022-09-04.12:18:27.701477|s|SAI_OBJECT_TYPE_HOSTIF:oid:0xd0000000005b3|SAI_HOSTIF_ATTR_VLAN_TAG=SAI_HOSTIF_VLAN_TAG_KEEP
    2022-09-04.12:18:27.703498|c|SAI_OBJECT_TYPE_VLAN_MEMBER:oid:0x27000000000626|SAI_VLAN_MEMBER_ATTR_VLAN_ID=oid:0x26000000000622|SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID=oid:0x3a000000000625|SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE=SAI_VLAN_TAGGING_MODE_UNTAGGED
    2022-09-04.12:18:27.705513|s|SAI_OBJECT_TYPE_PORT:oid:0x1000000000005|SAI_PORT_ATTR_PORT_VLAN_ID=10

    '''

    commands = [
        #CLI: sudo config vlan add 10
        {
            "name": "vlan_10",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_VLAN",
            "attributes": [
                "SAI_VLAN_ATTR_VLAN_ID", vlan_id
            ]
        },
        {
            "name": "route_entry_1",  # screate failure
            "op": "create",
            "type": "SAI_OBJECT_TYPE_ROUTE_ENTRY",
            "attributes": [
                'SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION', 'SAI_PACKET_ACTION_DROP',
            ],
            'key': {
                'switch_id': '$SWITCH_ID',
                'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
                'destination': '::/0',
            }
        },
        {
            "name": "route_entry_2",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_ROUTE_ENTRY",
            "attributes": [
                'SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION', 'SAI_PACKET_ACTION_DROP'
            ],
            'key': {
                'switch_id': '$SWITCH_ID',
                'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
                'destination': '0.0.0.0/0',
            },
        },
        {  # Sset" operation failure
            'name': 'route_entry_1',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_ROUTE_ENTRY',
            'attributes': ['SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION', 'SAI_PACKET_ACTION_DROP',
                           'SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', 'SAI_NULL_OBJECT_ID'],  # oid:0x0
            'key': {
                'switch_id': '$SWITCH_ID',
                'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
                'destination': '::/0',
            },
        },
        {
            'name': 'route_entry_2',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_ROUTE_ENTRY',
            'attributes': ['SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION', 'SAI_PACKET_ACTION_DROP',
                           'SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', 'SAI_NULL_OBJECT_ID', ],  # oid:0x0
            'key': {
                'switch_id': '$SWITCH_ID',
                'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
                'destination': '0.0.0.0/0',
            },
        },

        # CLI: sudo config vlan member add -u 10 Ethernet120
        { #pass
            'name': 'bridge_port_1',
            'op': 'create',
            'type': 'SAI_OBJECT_TYPE_BRIDGE_PORT',
            'attributes': ['SAI_BRIDGE_PORT_ATTR_TYPE', 'SAI_BRIDGE_PORT_TYPE_PORT',
                           'SAI_BRIDGE_PORT_ATTR_PORT_ID', '$PORT_30',  # oid:0x1000000000004
                           'SAI_BRIDGE_PORT_ATTR_ADMIN_STATE', 'true',
                           'SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE', 'SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW'],

        },
        { #set failure
            'name': 'host_interface_1',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_HOSTIF',
            'attributes': ['SAI_HOSTIF_ATTR_VLAN_TAG', 'SAI_HOSTIF_VLAN_TAG_KEEP'],
        },
        {
            'name': 'vlan_member_1',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_VLAN_MEMBER',
            'attributes': ['SAI_VLAN_MEMBER_ATTR_VLAN_ID', '$vlan_10',  # oid:0x26000000000622
                           'SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID', 'oid:0x3a000000000623',  # oid:0x3a000000000623
                           'SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE', 'SAI_VLAN_TAGGING_MODE_UNTAGGED'
                           ]
        },
        {
            'name': '$PORT_30',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_PORT',
            'attributes': ['SAI_PORT_ATTR_PORT_VLAN_ID', '10']
        },

        # CLI: sudo config vlan member add -u 10 Ethernet124
        {
            'name': 'bridge_port_2',
            'op': 'create',
            'type': 'SAI_OBJECT_TYPE_BRIDGE_PORT',
            'attributes': ['SAI_BRIDGE_PORT_ATTR_TYPE', 'SAI_BRIDGE_PORT_TYPE_PORT',
                           'SAI_BRIDGE_PORT_ATTR_PORT_ID', '$PORT_31',  # oid:0x1000000000004
                           'SAI_BRIDGE_PORT_ATTR_ADMIN_STATE', 'true',
                           'SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE', 'SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW'],

        },
        {
            'name': 'host_interface_2',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_HOSTIF',
            'attributes': ['SAI_HOSTIF_ATTR_VLAN_TAG', 'SAI_HOSTIF_VLAN_TAG_KEEP'],
        },
        {
            'name': 'vlan_member_2',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_VLAN_MEMBER',
            'attributes': ['SAI_VLAN_MEMBER_ATTR_VLAN_ID', '$vlan_10',  # oid:0x26000000000622
                           'SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID', 'oid:0x3a000000000623',  # oid:0x3a000000000623
                           'SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE', 'SAI_VLAN_TAGGING_MODE_UNTAGGED'
                           ],
        },
        {
            'name': '$PORT_31',
            'op': 'set',
            'type': 'SAI_OBJECT_TYPE_PORT',
            'attributes': ['SAI_PORT_ATTR_PORT_VLAN_ID', '10']
        }
    ]
    
    for command in commands:
        print('-'*80)
        pprint(command)
        result = npu.command_processor.process_command(command)
        pprint(result)

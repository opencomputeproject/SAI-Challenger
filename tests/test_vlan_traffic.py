import pytest
import snappi
import time
from pprint import pprint
#pp = pprint.PrettyPrinter(indent=4)
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
    #4. Set max learned addresses
    #5. Get max learned addresses
    #6. Get vlan member list
    #7. Send a simple vlan tag (10) packet on port 1 and verify packet on port 2
    #8. Clean up configuration
    """
    vlan_id = "10"

    '''
    CLI- sudo config vlan add 10
    SAI (DONE)
    2022-08-30.15:58:33.238851|c|SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x6000000000621|SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID=oid:0x3000000000022|SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS=A8:2B:B5:37:EB:1C|SAI_ROUTER_INTERFACE_ATTR_TYPE=SAI_ROUTER_INTERFACE_TYPE_PORT|SAI_ROUTER_INTERFACE_ATTR_PORT_ID=oid:0x1000000000009|SAI_ROUTER_INTERFACE_ATTR_MTU=9100|SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID=0
    2022-08-31.11:30:58.950357|c|SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x6000000000620|SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID=oid:0x3000000000022|SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS=A8:2B:B5:37:EB:1C|SAI_ROUTER_INTERFACE_ATTR_TYPE=SAI_ROUTER_INTERFACE_TYPE_PORT|SAI_ROUTER_INTERFACE_ATTR_PORT_ID=oid:0x1000000000008|SAI_ROUTER_INTERFACE_ATTR_MTU=9100|SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID=0
    2022-08-31.14:55:12.903012|c|SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"10.0.0.60/32","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_FORWARD|SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x1000000000032
    2022-08-30.15:58:32.746396|c|SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"10.0.0.62/32","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_FORWARD|SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x1000000000032


    |c|SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP
    2022-09-04.12:17:08.409539|c|SAI_OBJECT_TYPE_VLAN:oid:0x26000000000622|SAI_VLAN_ATTR_VLAN_ID=10

    2022-09-04.12:17:08.416163|S|SAI_OBJECT_TYPE_ROUTE_ENTRY||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    |SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0

    '''
    cmds=[ #pass
    {
        "name": "router_interface_1",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_ROUTER_INTERFACE",
        "attributes": [
            "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", "$DEFAULT_VIRTUAL_ROUTER_ID",
            "SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS", "A8:2B:B5:37:EB:1C",
            "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_PORT",
            "SAI_ROUTER_INTERFACE_ATTR_PORT_ID", "$PORT_30",
            "SAI_ROUTER_INTERFACE_ATTR_MTU", "9100",
            "SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID", "0"
        ]
    }]
    results = [*npu.process_command(cmds)]

    cmds=[ #pass
    {
        "name": "router_interface_2",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_ROUTER_INTERFACE",
        "attributes": [
            "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", "$DEFAULT_VIRTUAL_ROUTER_ID",
            "SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS", "A8:2B:B5:37:EB:1C",
            "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_PORT",
            "SAI_ROUTER_INTERFACE_ATTR_PORT_ID", "$PORT_31",
            "SAI_ROUTER_INTERFACE_ATTR_MTU", "9100",
            "SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID", "0"
        ]
    }]
    results = [*npu.process_command(cmds)]

    cmds=[  #pass
    {
        "name": "vlan_10",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_VLAN",
        "attributes": [
            "SAI_VLAN_ATTR_VLAN_ID", vlan_id
        ]
    }]
    results = [*npu.process_command(cmds)]

    cmds = [{
        "name": "route_entry_1",  #screate failure
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
    }]
    results = [*npu.process_command(cmds)]

    cmds = [{ #screate failure
        "name": "route_entry_1_1",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_ROUTE_ENTRY",
        "attributes": [
            'SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION', 'SAI_PACKET_ACTION_FORWARD',
            'SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', 'oid:0x600000000060b' #doubt oid:0x600000000060b
        ],
        'key': {
            'switch_id': '$SWITCH_ID',
            'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
            'destination': ':10.0.0.60/32',
        }
    }]

    results = [*npu.process_command(cmds)]

    cmds=[
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
    }]
    results = [*npu.process_command(cmds)]
    cmds = [{
        "name": "route_entry_2_1",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_ROUTE_ENTRY",
        "attributes": [
            'SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION', 'SAI_PACKET_ACTION_FORWARD',
            'SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', 'oid:0x600000000060b' #doubt
        ],
        'key': {
            'switch_id': '$SWITCH_ID',
            'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
            'destination': ':10.0.0.62/32',
        }
    }]
    results = [*npu.process_command(cmds)]
    cmds=[{  #Sset" operation failure
    'name': 'route_entry_1',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_ROUTE_ENTRY',
    'attributes': ['SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION' , 'SAI_PACKET_ACTION_DROP',
                    'SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', 'SAI_NULL_OBJECT_ID'], #oid:0x0
    'key': {
            'switch_id': '$SWITCH_ID',
            'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
            'destination': '::/0',
        },
    },
    ]
    results = [*npu.process_command(cmds)]

    cmds=[
    {
    'name': 'route_entry_2',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_ROUTE_ENTRY',
    'attributes': ['SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION','SAI_PACKET_ACTION_DROP',
                   'SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID', 'SAI_NULL_OBJECT_ID',], #oid:0x0
    'key': {
        'switch_id': '$SWITCH_ID',
        'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
        'destination': '0.0.0.0/0',
        },
    },
    ]
    results = [*npu.process_command(cmds)]

    '''
    CLI- sudo config vlan member add -u 10 Ethernet120
    SAI
    Adding vlan member -----------
    2022-09-04.12:17:51.643262|c|SAI_OBJECT_TYPE_BRIDGE_PORT:oid:0x3a000000000623|SAI_BRIDGE_PORT_ATTR_TYPE=SAI_BRIDGE_PORT_TYPE_PORT|SAI_BRIDGE_PORT_ATTR_PORT_ID=oid:0x1000000000004|SAI_BRIDGE_PORT_ATTR_ADMIN_STATE=true|SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE=SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW
    2022-09-04.12:17:51.645928|s|SAI_OBJECT_TYPE_HOSTIF:oid:0xd0000000005b2|SAI_HOSTIF_ATTR_VLAN_TAG=SAI_HOSTIF_VLAN_TAG_KEEP
    2022-09-04.12:17:51.648374|c|SAI_OBJECT_TYPE_VLAN_MEMBER:oid:0x27000000000624|SAI_VLAN_MEMBER_ATTR_VLAN_ID=oid:0x26000000000622|SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID=oid:0x3a000000000623|SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE=SAI_VLAN_TAGGING_MODE_UNTAGGED
    2022-09-04.12:17:51.651184|s|SAI_OBJECT_TYPE_PORT:oid:0x1000000000004|SAI_PORT_ATTR_PORT_VLAN_ID=10
    2022-09-04.12:17:51.655250|n|fdb_event|[{"fdb_entry":"{\"bvid\":\"oid:0x26000000000622\",\"mac\":\"00:22:22:22:22:22\",\"switch_id\":\"oid:0x21000000000000\"}","fdb_event":"SAI_FDB_EVENT_LEARNED","list":[{"id":"SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID","value":"oid:0x3a000000000623"}]}]|
    '''
    cmds=[ #pass
    {
    'name': 'bridge_port_1',
    'op': 'create',
    'type': 'SAI_OBJECT_TYPE_BRIDGE_PORT',
    'attributes': ['SAI_BRIDGE_PORT_ATTR_TYPE','SAI_BRIDGE_PORT_TYPE_PORT',
                   'SAI_BRIDGE_PORT_ATTR_PORT_ID', '$PORT_30', # oid:0x1000000000004
                   'SAI_BRIDGE_PORT_ATTR_ADMIN_STATE', 'true',
                   'SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE', 'SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW'],

    },
    ]
    results = [*npu.process_command(cmds)]
    cmds=[ #"Sset" operation failure!
    {
    'name': 'host_interface_1',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_HOSTIF',
    'attributes': ['SAI_HOSTIF_ATTR_VLAN_TAG','SAI_HOSTIF_VLAN_TAG_KEEP'],
    },
    ]
    results = [*npu.process_command(cmds)]
    cmds=[ #Sset failure
    {
    'name': 'vlan_member_1',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_VLAN_MEMBER',
    'attributes': ['SAI_VLAN_MEMBER_ATTR_VLAN_ID','$vlan_10', #oid:0x26000000000622
                    'SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID','$BRIDGE_PORT_30', #oid:0x3a000000000623
                    'SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE','SAI_VLAN_TAGGING_MODE_UNTAGGED'
                  ]
    },
    ]
    results = [*npu.process_command(cmds)]
    cmds=[ #Sset" operation failure
    {
    'name': '$PORT_30',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_PORT',
    'attributes': ['SAI_PORT_ATTR_PORT_VLAN_ID','10']
    }
    ]
    results = [*npu.process_command(cmds)]

    '''
    CLI- sudo config vlan member add -u 10 Ethernet124
    SAI:
    2022-09-04.12:18:27.699269|c|SAI_OBJECT_TYPE_BRIDGE_PORT:oid:0x3a000000000625|SAI_BRIDGE_PORT_ATTR_TYPE=SAI_BRIDGE_PORT_TYPE_PORT|SAI_BRIDGE_PORT_ATTR_PORT_ID=oid:0x1000000000005|SAI_BRIDGE_PORT_ATTR_ADMIN_STATE=true|SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE=SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW
    2022-09-04.12:18:27.701477|s|SAI_OBJECT_TYPE_HOSTIF:oid:0xd0000000005b3|SAI_HOSTIF_ATTR_VLAN_TAG=SAI_HOSTIF_VLAN_TAG_KEEP
    2022-09-04.12:18:27.703498|c|SAI_OBJECT_TYPE_VLAN_MEMBER:oid:0x27000000000626|SAI_VLAN_MEMBER_ATTR_VLAN_ID=oid:0x26000000000622|SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID=oid:0x3a000000000625|SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE=SAI_VLAN_TAGGING_MODE_UNTAGGED
    2022-09-04.12:18:27.705513|s|SAI_OBJECT_TYPE_PORT:oid:0x1000000000005|SAI_PORT_ATTR_PORT_VLAN_ID=10
    '''

    cmds=[ #pass
    {
    'name': 'bridge_port_2',
    'op': 'create',
    'type': 'SAI_OBJECT_TYPE_BRIDGE_PORT',
    'attributes': ['SAI_BRIDGE_PORT_ATTR_TYPE','SAI_BRIDGE_PORT_TYPE_PORT',
                   'SAI_BRIDGE_PORT_ATTR_PORT_ID', '$PORT_31', # oid:0x1000000000004
                   'SAI_BRIDGE_PORT_ATTR_ADMIN_STATE', 'true',
                   'SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE', 'SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW'],

    },
    ]
    results = [*npu.process_command(cmds)]
    cmds=[ #Sset" operation failure
    {
    'name': 'host_interface_2',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_HOSTIF',
    'attributes': ['SAI_HOSTIF_ATTR_VLAN_TAG','SAI_HOSTIF_VLAN_TAG_KEEP'],
    },
    ]
    results = [*npu.process_command(cmds)]
    cmds=[ #Sset" operation failure
    {
    'name': 'vlan_member_2',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_VLAN_MEMBER',
    'attributes': ['SAI_VLAN_MEMBER_ATTR_VLAN_ID','$vlan_10', #oid:0x26000000000622
                    'SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID','BRIDGE_PORT_31', #oid:0x3a000000000623
                    'SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE','SAI_VLAN_TAGGING_MODE_UNTAGGED'
                  ], 
    },
    ]
    results = [*npu.process_command(cmds)]
    cmds=[ #Sset" operation failure
    {
    'name': '$PORT_31',
    'op': 'set',
    'type': 'SAI_OBJECT_TYPE_PORT',
    'attributes': ['SAI_PORT_ATTR_PORT_VLAN_ID','10']
    }
    ]
    results = [*npu.process_command(cmds)]

    '''
    CLI: sudo config interface ip remove Ethernet120 10.0.0.60/31
    SAI:
    2022-09-04.12:15:14.577228|r|SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"10.0.0.60/32","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    2022-09-04.12:15:14.592580|R|SAI_OBJECT_TYPE_ROUTE_ENTRY||{"dest":"10.0.0.60/31","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    2022-09-04.12:15:14.594681|S|SAI_OBJECT_TYPE_ROUTE_ENTRY||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0
    2022-09-04.12:15:14.610137|r|SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x6000000000620
    '''
    cmds=[
    {
    'name': 'route_entry_1_1',  
    'op': 'remove',
    'type': 'SAI_OBJECT_TYPE_ROUTE_ENTRY',
        'key': {
            'switch_id': '$SWITCH_ID',
            'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
            'destination': '10.0.0.60/32',
        }
    }
    ]
    results = [*npu.process_command(cmds)]
    cmds=[
    {
    'name': 'router_interface_1',  
    'op': 'remove',
    }
    ]
    results = [*npu.process_command(cmds)]

    '''
    CLI: sudo config interface ip remove Ethernet124 10.0.0.62/3
    SAI:
    2022-09-04.12:15:57.490897|r|SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"10.0.0.62/32","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    2022-09-04.12:15:57.501720|R|SAI_OBJECT_TYPE_ROUTE_ENTRY||{"dest":"10.0.0.62/31","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
    2022-09-04.12:15:57.504497|S|SAI_OBJECT_TYPE_ROUTE_ENTRY||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"::/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION=SAI_PACKET_ACTION_DROP||{"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}|SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID=oid:0x0
    2022-09-04.12:15:57.525035|r|SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x6000000000621
    '''
    cmds=[
    {
    'name': 'route_entry_2_1',  
    'op': 'remove',
    'type': 'SAI_OBJECT_TYPE_ROUTE_ENTRY',
        'key': {
            'switch_id': '$SWITCH_ID',
            'vr_id': '$DEFAULT_VIRTUAL_ROUTER_ID',
            'destination': '10.0.0.62/32',
        }
    }
    ]
    results = [*npu.process_command(cmds)]

    cmds=[
    {
    'name': 'route_entry_2',  
    'op': 'remove',
    }
    ]
    results = [*npu.process_command(cmds)]


    '''
    for switch in npu.switch_oid:
        import pdb;pdb.set_trace()
        status, data = npu.get_by_type(switch, "SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", "sai_uint32_t", do_assert = False)
        pprint(data.data)

    #status, data = npu.get_by_type(switch_oid, "SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", "sai_uint32_t", do_assert = False)
    #pprint(data.data)
    for port in npu.port_oids:
        npu.set(port, ["SAI_PORT_ATTR_ADMIN_STATE","true"], False)
        #npu.set(port, ["SAI_PORT_ATTR_PORT_VLAN_ID","10"], False)
    time.sleep(10)
    for port in npu.port_oids:
        status, data = npu.get_by_type(port, "SAI_PORT_ATTR_OPER_STATUS", "sai_port_oper_status_t", do_assert = False)
        pprint(data.data)
        status, data = npu.get_by_type(port, "SAI_PORT_ATTR_PORT_VLAN_ID", "sai_uint16_t", do_assert = False)
        pprint(data.data)   
        import pdb;pdb.set_trace()

        
    try:
        location = "https://" + '10.36.78.145' + ":" + str(443)
        api = snappi.api(location=location, ext="ixnetwork")
        config = api.config()
        p1, p2 = (
            config.ports.port(name="txp1", location='10.36.78.53;6;7')
            .port(name="txp2", location='10.36.78.53;6;8')
        )
        config.options.port_options.location_preemption = True
        layer1 = config.layer1.layer1()[-1]
        layer1.name = 'port settings'
        layer1.port_names = [port.name for port in config.ports]
        layer1.ieee_media_defaults = False
        layer1.auto_negotiation.rs_fec = False
        layer1.auto_negotiation.link_training = False
        layer1.speed = 'speed_100_gbps'
        layer1.auto_negotiate = False
        flow1 = config.flows.flow(name="Vlan Traffic")[-1]
        flow1.tx_rx.port.tx_name = p1.name
        flow1.tx_rx.port.rx_name = p2.name
        flow1.size.fixed = 1024
        flow1.rate.percentage = 100
        flow1.metrics.enable = True
        flow1.metrics.loss = True

        source = macs[1]
        destination = macs[0]
        ether_type = 33024

        eth, vlan = flow1.packet.ethernet().vlan()

        eth.src.value = source
        eth.dst.value = destination
        #eth.ether_type.value = ether_type

        vlan.id.value = int(vlan_id)
        api.set_config(config)

        ts = api.transmit_state()
        ts.flow_names = [flow1.name]
        ts.state = ts.START
        api.set_transmit_state(ts)
        time.sleep(10)
        ts = api.transmit_state()
        ts.flow_names = [flow1.name]
        ts.state = ts.STOP
        api.set_transmit_state(ts)
        time.sleep(6)
        request = api.metrics_request()
        request.flow.flow_names = [flow1.name]
        rows = api.get_metrics(request).flow_metrics
        assert(int(rows[0].loss) == 0, "loss observed")
        pprint('Tx_Frame Rate {}'.format(rows[0].frames_tx_rate))
        pprint('Rx_Frame Rate {}'.format(rows[0].frames_rx_rate))
        pprint('Loss {}'.format(rows[0].loss))
    finally:
        status = [*npu.process_command(cmds, cleanup=True)]
    '''

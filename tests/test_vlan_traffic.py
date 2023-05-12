import pytest
import snappi
import time
from pprint import pprint
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
    vlan_learned_max = "512"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']

    cmds = [   
    {
        "name": "vlan_10",
        "op": "create",
        "type": "SAI_OBJECT_TYPE_VLAN",
        "attributes": [
            "SAI_VLAN_ATTR_VLAN_ID", vlan_id
        ]
    }
    ]

    for i in range(0,32):
    #for i, mac in enumerate(macs):
        cmds.append(
        {
            'name': f"bridge_port_{i}",
            'op': 'create',
            'type': 'SAI_OBJECT_TYPE_BRIDGE_PORT',
            'attributes': ['SAI_BRIDGE_PORT_ATTR_TYPE', 'SAI_BRIDGE_PORT_TYPE_PORT',
                           'SAI_BRIDGE_PORT_ATTR_PORT_ID', f'$PORT_{i}',
                           'SAI_BRIDGE_PORT_ATTR_ADMIN_STATE', 'true',
                           'SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE', 'SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW'],

        }
        )
        cmds.append(
        {
            "name": f"vlan_member_{i}",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_VLAN_MEMBER",
            "attributes": ["SAI_VLAN_MEMBER_ATTR_VLAN_ID", "$vlan_10",  
                            "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", f"$BRIDGE_PORT_{i}",
                            "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", "SAI_VLAN_TAGGING_MODE_TAGGED"
                            ]
        })
        cmds.append(
        {
            "name": f"fdb_{i}",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_FDB_ENTRY",
            "key": {
                "bv_id": "$vlan_10",
                "mac_address": macs[i%2],
                "switch_id" : "$SWITCH_ID"
            },
            "attributes": [
                "SAI_FDB_ENTRY_ATTR_TYPE", "SAI_FDB_ENTRY_TYPE_STATIC",
                "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", f"$BRIDGE_PORT_{i}",
                "SAI_FDB_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"
            ]
        }
        )
    #status = [*npu.process_commands(cmds)]
    for command in cmds:
        print('-'*80)
        print(command)
        result = npu.command_processor.process_command(command)
        print(result)

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
        print('Tx_Frame Rate {}'.format(rows[0].frames_tx_rate))
        print('Rx_Frame Rate {}'.format(rows[0].frames_rx_rate))
        print('Loss {}'.format(rows[0].loss))
    finally:
            status = [*npu.process_commands(cmds, cleanup=True)]

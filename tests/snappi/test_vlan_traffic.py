import pytest
import time
from pprint import pprint as pprint

vlan_id = "10"
macs = ["00:1A:C5:00:00:01", "00:1B:6E:00:00:01"]


@pytest.fixture(scope="module", autouse=True)
def discovery(npu):
    npu.objects_discovery()


def test_l2_traffic(npu, dataplane):
    """
    Creates vlan 10 and adds two ports to the vlan 10 member
    and validates the config using l2 traffic
    """
    commands = [
        {
            "name": "vlan_10",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_VLAN",
            "attributes": ["SAI_VLAN_ATTR_VLAN_ID", "10"],
        },
        {
            "name": "bridge_p_2",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_BRIDGE_PORT",
            "attributes": [
                "SAI_BRIDGE_PORT_ATTR_TYPE",
                "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                "$PORT_2",
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                "true",
                "SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",
                "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW",
            ],
        },
        {
            "name": "vlan_member_2",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_VLAN_MEMBER",
            "attributes": [
                "SAI_VLAN_MEMBER_ATTR_VLAN_ID",
                "$vlan_10",
                "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",
                "$bridge_p_2",
                "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE",
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            ],
        },
        {
            "name": "PORT_2",
            "op": "set",
            "type": "SAI_OBJECT_TYPE_PORT",
            "attributes": [
                "SAI_PORT_ATTR_ADMIN_STATE",
                "true",
                "SAI_PORT_ATTR_PORT_VLAN_ID",
                "10",
            ],
        },
        {
            "name": "bridge_p_3",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_BRIDGE_PORT",
            "attributes": [
                "SAI_BRIDGE_PORT_ATTR_TYPE",
                "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID",
                "$PORT_3",
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE",
                "true",
                "SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE",
                "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW",
            ],
        },
        {
            "name": "vlan_member_3",
            "op": "create",
            "type": "SAI_OBJECT_TYPE_VLAN_MEMBER",
            "attributes": [
                "SAI_VLAN_MEMBER_ATTR_VLAN_ID",
                "$vlan_10",
                "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",
                "$bridge_p_3",
                "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE",
                "SAI_VLAN_TAGGING_MODE_UNTAGGED",
            ],
        },
        {
            "name": "PORT_3",
            "op": "set",
            "type": "SAI_OBJECT_TYPE_PORT",
            "attributes": [
                "SAI_PORT_ATTR_ADMIN_STATE",
                "true",
                "SAI_PORT_ATTR_PORT_VLAN_ID",
                "10",
            ],
        },
    ]
    for command in commands:
        print("-" * 80)
        print(command)
        result = npu.command_processor.process_command(command)
        print(result)

    macs = ["00:11:11:11:11:11", "00:22:22:22:22:22"]
    config = dataplane.configuration
    config.options.port_options.location_preemption = True
    layer1 = config.layer1.layer1()[-1]
    layer1.name = "port settings"
    layer1.port_names = [port.name for port in config.ports]
    layer1.ieee_media_defaults = False
    layer1.auto_negotiation.rs_fec = False
    layer1.auto_negotiation.link_training = False
    layer1.speed = "speed_100_gbps"
    layer1.auto_negotiate = False
    flow1 = config.flows.flow(name="Vlan Traffic")[-1]

    flow1.tx_rx.port.tx_name = config.ports[0].name
    flow1.tx_rx.port.rx_name = config.ports[1].name
    flow1.size.fixed = 1024
    flow1.rate.percentage = 100
    flow1.metrics.enable = True
    flow1.metrics.loss = True
    source = macs[1]
    destination = macs[0]
    eth, vlan = flow1.packet.ethernet().vlan()
    eth.src.value = source
    eth.dst.value = destination
    vlan.id.value = int(vlan_id)

    dataplane.set_config()
    restpy_session = dataplane.api.assistant.Session
    ixnet = restpy_session.Ixnetwork
    for port in ixnet.Vport.find():
        port.L1Config.NovusHundredGigLan.AutoInstrumentation = "endOfFrame"

    ts = dataplane.api.transmit_state()
    ts.flow_names = [flow1.name]
    ts.state = ts.START
    dataplane.api.set_transmit_state(ts)
    time.sleep(10)
    ts = dataplane.api.transmit_state()
    ts.flow_names = [flow1.name]
    ts.state = ts.STOP
    dataplane.api.set_transmit_state(ts)
    time.sleep(10)
    request = dataplane.api.metrics_request()
    request.flow.flow_names = [flow1.name]
    rows = dataplane.api.get_metrics(request).flow_metrics
    print("Loss {}".format(rows[0].loss))

    req = dataplane.api.metrics_request()
    req.port.port_names = [p.name for p in config.ports]
    req.port.column_names = [req.port.FRAMES_TX, req.port.FRAMES_RX]
    # fetch port metrics
    res = dataplane.api.get_metrics(req)
    total_tx = sum([m.frames_tx for m in res.port_metrics])
    total_rx = sum([m.frames_rx for m in res.port_metrics])
    print("Tx_Frame : {}".format(total_tx))
    print("Rx_Frame : {}".format(total_rx))
    assert total_tx == total_rx, "Tx Frame not equal to Rx Frame"
    assert int(rows[0].loss) == 0, "Loss observed"
    assert total_tx > 0, "Tx Frame rate is Zero"


@pytest.mark.dependency(depends=["test_l2_traffic"])
def test_cleanup(self, npu):
    commands = [
        {
            'name': 'vlan_10',
            'op': 'remove',
        },
        {
            'name': 'bridge_p_2',
            'op': 'remove',
        },
        {
            'name': 'vlan_member_2',
            'op': 'remove',
        },
        {
            'name': 'PORT_2',
            'op': 'remove',
        },
        {
            'name': 'bridge_p_3',
            'op': 'remove',
        },
        {
            'name': 'vlan_member_3',
            'op': 'remove',
        },
        {
            'name': 'PORT_3',
            'op': 'remove',
        }
    ]

    results = [*npu.process_commands(commands)]
    print('======= SAI commands RETURN values remove =======')
    pprint(results)

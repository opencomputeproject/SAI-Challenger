from pprint import pprint

import pytest

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dpu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))


@pytest.mark.dpu
class TestSaiOutboundRoutingEntry:
    # object with no attributes

    def test_outbound_routing_entry_create(self, dpu):
        commands = [
            {"name": "vnet","op": "create","type": "SAI_OBJECT_TYPE_VNET","attributes": ["SAI_VNET_ATTR_VNI","2000"]},
            {
                "name": "eni_1",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_ENI",
                "attributes": [
                    "SAI_ENI_ATTR_ADMIN_STATE","True",
                    "SAI_ENI_ATTR_VM_UNDERLAY_DIP","10.10.1.10",
                    "SAI_ENI_ATTR_VM_VNI","2000",
                    "SAI_ENI_ATTR_VNET_ID","$vnet",
            ]
            },        
            {
                'name': 'outbound_routing_entry_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_OUTBOUND_ROUTING_ENTRY',
                'attributes': ["SAI_OUTBOUND_ROUTING_ENTRY_ATTR_ACTION", "SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET","SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DST_VNET_ID", "$vnet"],
                'key': {
                    'switch_id': '$SWITCH_ID',
                    'eni_id': '$eni_1',
                    'destination': '10.1.0.0/16',
                },
            }
        ]

        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values create =======\n')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_outbound_routing_entry_attr_action_set')
    def test_sai_outbound_routing_entry_attr_action_set(self, dpu):
        commands = [
            {
                'name': 'outbound_routing_entry_1',
                'op': 'set',
                'attributes': [
                    'SAI_OUTBOUND_ROUTING_ENTRY_ATTR_ACTION',
                    'SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET',
                    "SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DST_VNET_ID", "$vnet"
                ],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values set =======\n')
        pprint(results)


    @pytest.mark.dependency(name='test_sai_outbound_routing_entry_attr_dst_vnet_id_set')
    def test_sai_outbound_routing_entry_attr_dst_vnet_id_set(self, dpu):
        commands = [
            {
                'name': 'outbound_routing_entry_1',
                'op': 'set',
                'attributes': [
                    'SAI_OUTBOUND_ROUTING_ENTRY_ATTR_ACTION',
                    'SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET',
                    "SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DST_VNET_ID", "$vnet"
                ],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values set =======\n')
        pprint(results)




    @pytest.mark.dependency(name='test_sai_outbound_routing_entry_attr_overlay_ip_set')
    def test_sai_outbound_routing_entry_attr_overlay_ip_set(self, dpu):
        commands = [
            {
                'name': 'outbound_routing_entry_1',
                'op': 'set',
                'attributes': ['SAI_OUTBOUND_ROUTING_ENTRY_ATTR_OVERLAY_IP', '0.0.0.0'],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values set =======\n')
        pprint(results)


    @pytest.mark.dependency(name='test_sai_outbound_routing_entry_attr_counter_id_set')
    def test_sai_outbound_routing_entry_attr_counter_id_set(self, dpu):
        commands = [
            {
                'name': 'outbound_routing_entry_1',
                'op': 'set',
                'attributes': ['SAI_OUTBOUND_ROUTING_ENTRY_ATTR_COUNTER_ID', 'null'],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values set =======\n')
        pprint(results)



    def test_outbound_routing_entry_remove(self, dpu):
        commands = [
            {
                'name': 'outbound_routing_entry_1',
                'key': {
                    'switch_id': '$SWITCH_ID',
                    'eni_id': '$eni_1',
                    'destination': '10.1.0.0/16',
                },
                'op': 'remove',
            },
            {'name': 'eni_1', 'op': 'remove'},
            {"name": "vnet","op": "remove"},            
            
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

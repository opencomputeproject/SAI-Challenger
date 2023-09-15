
from pprint import pprint

import pytest

@pytest.mark.dpu
class TestSaiInboundRoutingEntry:
    # object with no attributes

    def test_inbound_routing_entry_create(self, dpu):

        commands = [
            {"name": "vnet","op": "create","type": "SAI_OBJECT_TYPE_VNET","attributes": ["SAI_VNET_ATTR_VNI","2000"]},
            {"name": "eni_1","op": "create","type": "SAI_OBJECT_TYPE_ENI",
                "attributes": [
                                "SAI_ENI_ATTR_ADMIN_STATE","True",
                                "SAI_ENI_ATTR_VM_UNDERLAY_DIP","10.10.1.10",
                                "SAI_ENI_ATTR_VM_VNI","2000",
                                "SAI_ENI_ATTR_VNET_ID","$vnet",
                                ]
            },
            {'name': 'inbound_routing_entry_1', 'op': 'create', 'type': 'SAI_OBJECT_TYPE_INBOUND_ROUTING_ENTRY', 
                'attributes': [
                                "SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION","SAI_INBOUND_ROUTING_ENTRY_ACTION_VXLAN_DECAP_PA_VALIDATE",
                                "SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID","$vnet"
                            ], 
                'key': {'switch_id': '$SWITCH_ID', 'eni_id': "33", 'vni': '2000', 'sip': '1.1.1.1', 'sip_mask': '32', 'priority': '0'}
            }
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_inbound_routing_entry_attr_action_set")
    def test_sai_inbound_routing_entry_attr_action_set(self, dpu):

        commands = [
            {
                "name": "inbound_routing_entry_1",
                "op": "set",
                "attributes": [
					"SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION",
					'SAI_INBOUND_ROUTING_ENTRY_ACTION_VXLAN_DECAP'
				],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)

    @pytest.mark.dependency(name="test_sai_inbound_routing_entry_attr_src_vnet_id_set")
    def test_sai_inbound_routing_entry_attr_src_vnet_id_set(self, dpu):

        commands = [
            {
                "name": "inbound_routing_entry_1",
                "op": "set",
                "attributes": ["SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID", '0']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    def test_inbound_routing_entry_remove(self, dpu):

        commands = [
            {
                'name': 'inbound_routing_entry_1',
                'op': 'remove',
                'key': 
                    {
                        'switch_id': '$SWITCH_ID',
                        'eni_id': '33',
                        'vni': '2000',
                        'sip': '1.1.1.1',
                        'sip_mask': '32',
                        'priority': '0'
                    },
            },
            {'name': 'eni_1', 'op': 'remove'},
            {"name": "vnet","op": "remove"},
        ]
        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


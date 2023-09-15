
from pprint import pprint

import pytest

@pytest.mark.dpu
class TestSaiOutboundCaToPaEntry:
    # object with no attributes

    def test_outbound_ca_to_pa_entry_create(self, dpu):

        commands = [
            {
                "name": "vnet",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_VNET",
                "attributes": ["SAI_VNET_ATTR_VNI","2000"]
            },
            {
                'name': 'outbound_ca_to_pa_entry_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_OUTBOUND_CA_TO_PA_ENTRY', 
                'attributes': [
                      "SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_UNDERLAY_DIP","221.0.2.100",
                      "SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_DMAC","00:1B:6E:00:00:01",
                      "SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_USE_DST_VNET_VNI","True",
                ], 
                'key': {'switch_id': '$SWITCH_ID', 'dst_vnet_id': '$vnet', 'dip': '1.128.0.1'}
            }
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_outbound_ca_to_pa_entry_attr_underlay_dip_set")
    def test_sai_outbound_ca_to_pa_entry_attr_underlay_dip_set(self, dpu):

        commands = [
            {
                "name": "outbound_ca_to_pa_entry_1",
                "op": "set",
                "attributes": ["SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_UNDERLAY_DIP", '0.0.0.0']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)



    @pytest.mark.dependency(name="test_sai_outbound_ca_to_pa_entry_attr_overlay_dmac_set")
    def test_sai_outbound_ca_to_pa_entry_attr_overlay_dmac_set(self, dpu):

        commands = [
            {
                "name": "outbound_ca_to_pa_entry_1",
                "op": "set",
                "attributes": ["SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_DMAC", '0:0:0:0:0:0']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    @pytest.mark.dependency(name="test_sai_outbound_ca_to_pa_entry_attr_use_dst_vnet_vni_set")
    def test_sai_outbound_ca_to_pa_entry_attr_use_dst_vnet_vni_set(self, dpu):

        commands = [
            {
                "name": "outbound_ca_to_pa_entry_1",
                "op": "set",
                "attributes": ["SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_USE_DST_VNET_VNI", 'false']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    @pytest.mark.dependency(name="test_sai_outbound_ca_to_pa_entry_attr_counter_id_set")
    def test_sai_outbound_ca_to_pa_entry_attr_counter_id_set(self, dpu):

        commands = [
            {
                "name": "outbound_ca_to_pa_entry_1",
                "op": "set",
                "attributes": ["SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_COUNTER_ID", '0']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    def test_outbound_ca_to_pa_entry_remove(self, dpu):

        commands = [
            {
                'name': 'outbound_ca_to_pa_entry_1',
                'op': 'remove',
                'key': 
                    {
                    'switch_id': '$SWITCH_ID',
                    'dst_vnet_id': '$vnet',
                    'dip': '1.128.0.1'
                    },
            },
            {"name": "vnet","op": "remove"},
                    
        ]
        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


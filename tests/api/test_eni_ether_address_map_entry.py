from pprint import pprint

import pytest

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dpu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

@pytest.mark.dpu
class TestSaiEniEtherAddressMapEntry:
    # object with no attributes

    def test_eni_ether_address_map_entry_create(self, dpu):
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
                'name': 'eni_ether_address_map_entry_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ENI_ETHER_ADDRESS_MAP_ENTRY',
                'attributes': ["SAI_ENI_ETHER_ADDRESS_MAP_ENTRY_ATTR_ENI_ID","$eni_1"],
                'key': {'switch_id': '$SWITCH_ID', 'address': '00:AA:AA:AA:AB:00'},
            }
        ]

        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values create =======\n')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_eni_ether_address_map_entry_attr_eni_id_set')
    def test_sai_eni_ether_address_map_entry_attr_eni_id_set(self, dpu):
        commands = [
            {
                'name': 'eni_ether_address_map_entry_1',
                'op': 'set',
                'attributes': ['SAI_ENI_ETHER_ADDRESS_MAP_ENTRY_ATTR_ENI_ID', 'null'],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values set =======\n')
        pprint(results)


    def test_eni_ether_address_map_entry_remove(self, dpu):
        commands = [
        
            {
                'name': 'eni_ether_address_map_entry_1',
                'key': {'switch_id': '$SWITCH_ID', 'address': '00:AA:AA:AA:AB:00'},
                'op': 'remove',
            },
            {'name': 'eni_1', 'op': 'remove'},
            {"name": "vnet","op": "remove"},            
        ]

        results = [*dpu.process_commands(commands)]
        print('\n======= SAI commands RETURN values remove =======\n')
        pprint(results)


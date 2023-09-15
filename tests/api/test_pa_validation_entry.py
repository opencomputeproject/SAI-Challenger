
from pprint import pprint

import pytest

@pytest.mark.dpu
class TestSaiPaValidationEntry:
    # object with no attributes

    def test_pa_validation_entry_create(self, dpu):

        commands = [
            {
                "name": "vnet",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_VNET",
                "attributes": ["SAI_VNET_ATTR_VNI","7000"]
            },
            {
                'name': 'pa_validation_entry_1', 
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_PA_VALIDATION_ENTRY',
                'attributes': [], 
                'key': 
                    {
                        'switch_id': '$SWITCH_ID',
                        'vnet_id': '$vnet',
                        'sip': '1.1.1.1'
                    }
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_pa_validation_entry_attr_action_set")
    def test_sai_pa_validation_entry_attr_action_set(self, dpu):

        commands = [
            {
                "name": "pa_validation_entry_1",
                "op": "set",
                "attributes": [
                    "SAI_PA_VALIDATION_ENTRY_ATTR_ACTION",
                    'SAI_PA_VALIDATION_ENTRY_ACTION_PERMIT'
                ],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)

    def test_pa_validation_entry_remove(self, dpu):

        commands = [
            {
                'name': 'pa_validation_entry_1',
                'op': 'remove',
                'key': 
                    {
                    'switch_id': '$SWITCH_ID',
                    'vnet_id': '$vnet',
                    'sip': '1.1.1.1'
                    }, 
            }
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


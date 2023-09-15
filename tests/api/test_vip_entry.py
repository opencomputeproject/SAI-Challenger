
from pprint import pprint

import pytest

@pytest.mark.dpu
class TestSaiVipEntry:
    # object with no attributes

    def test_vip_entry_create(self, dpu):

        commands = [
            {
                'name': 'vip_entry_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_VIP_ENTRY',
                'attributes': [],
                'key': {'switch_id': '$SWITCH_ID', 'vip': '1.2.1.1'}
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_vip_entry_attr_action_set")
    def test_sai_vip_entry_attr_action_set(self, dpu):

        commands = [
            {
                "name": "vip_entry_1",
                "op": "set",
                "attributes": ["SAI_VIP_ENTRY_ATTR_ACTION", 'SAI_VIP_ENTRY_ACTION_ACCEPT']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    def test_vip_entry_remove(self, dpu):

        commands = [{'name': 'vip_entry_1', 'key': {'switch_id': '$SWITCH_ID', 'vip': '1.2.1.1'}, 'op': 'remove'}]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


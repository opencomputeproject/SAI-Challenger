
from pprint import pprint

import pytest

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dpu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

@pytest.mark.dpu
class TestSaiDirectionLookupEntry:
    # object with no attributes

    def test_direction_lookup_entry_create(self, dpu):
        commands = [
            {
                'name': 'direction_lookup_entry_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DIRECTION_LOOKUP_ENTRY',
                'attributes': [],
                'key': {'switch_id': '$SWITCH_ID', 'vni': "2000"}
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_direction_lookup_entry_attr_action_set")
    def test_sai_direction_lookup_entry_attr_action_set(self, dpu):

        commands = [
            {
                "name": "direction_lookup_entry_1",
                "op": "set",
                "attributes": ["SAI_DIRECTION_LOOKUP_ENTRY_ATTR_ACTION", 'SAI_DIRECTION_LOOKUP_ENTRY_ACTION_SET_OUTBOUND_DIRECTION']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    def test_direction_lookup_entry_remove(self, dpu):

        commands = [{'name': 'direction_lookup_entry_1', 'key': {'switch_id': '$SWITCH_ID', 'vni': '2000'}, 'op': 'remove'}]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


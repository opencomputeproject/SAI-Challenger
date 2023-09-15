
from pprint import pprint

import pytest

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dpu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

@pytest.mark.dpu
class TestSaiVnet:
    # object with no attributes

    def test_vnet_create(self, dpu):

        commands = [
			{
				'name': 'vnet_1', 
				'op': 'create', 
				'type': 'SAI_OBJECT_TYPE_VNET', 
				'attributes': ["SAI_VNET_ATTR_VNI", '2001']
			}
		]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)


    @pytest.mark.dependency(name="test_sai_vnet_attr_vni_set")
    def test_sai_vnet_attr_vni_set(self, dpu):

        commands = [
            {
                "name": "vnet_1",
                "op": "set",
                "attributes": ["SAI_VNET_ATTR_VNI", '2001']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    def test_vnet_remove(self, dpu):

        commands = [{'name': 'vnet_1', 'op': 'remove'}]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


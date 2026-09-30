
from pprint import pprint

import pytest


@pytest.fixture(scope="module", autouse=True)
def discovery(npu):
    npu.objects_discovery()


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for {} testbed".format(testbed.name))


@pytest.mark.npu
class TestSaiNextHopGroup:
    # object with no parents

    def test_next_hop_group_create(self, npu):

        commands = [{'name': 'next_hop_group_1', 'op': 'create', 'type': 'SAI_OBJECT_TYPE_NEXT_HOP_GROUP', 'attributes': ['SAI_NEXT_HOP_GROUP_ATTR_TYPE', 'SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_UNORDERED_ECMP']}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)


    @pytest.mark.dependency(name="test_sai_next_hop_group_attr_set_switchover_set")
    def test_sai_next_hop_group_attr_set_switchover_set(self, npu):

        commands = [
            {
                "name": "next_hop_group_1",
                "op": "set",
                "attributes": ["SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER", 'false']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_next_hop_group_attr_set_switchover_set"])
    def test_sai_next_hop_group_attr_set_switchover_get(self, npu):

        commands = [
            {
                "name": "next_hop_group_1",
                "op": "get",
                "attributes": ["SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'false', 'Get error, expected false but got %s' %  r_value


    def test_next_hop_group_remove(self, npu):

        commands = [{'name': 'next_hop_group_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


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


class TestSaiHostifTrapGroup:
    # object with no attributes

    def test_hostif_trap_group_create(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_hostif_trap_group_attr_admin_state_set')
    def test_sai_hostif_trap_group_attr_admin_state_set(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'set',
                'attributes': ['SAI_HOSTIF_TRAP_GROUP_ATTR_ADMIN_STATE', 'true'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_hostif_trap_group_attr_admin_state_set'])
    def test_sai_hostif_trap_group_attr_admin_state_get(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'get',
                'attributes': ['SAI_HOSTIF_TRAP_GROUP_ATTR_ADMIN_STATE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'true', 'Get error, expected true but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_hostif_trap_group_attr_queue_set')
    def test_sai_hostif_trap_group_attr_queue_set(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'set',
                'attributes': ['SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_hostif_trap_group_attr_queue_set'])
    def test_sai_hostif_trap_group_attr_queue_get(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'get',
                'attributes': ['SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' % r_value

    def test_hostif_trap_group_remove(self, npu):
        commands = [{'name': 'hostif_trap_group_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

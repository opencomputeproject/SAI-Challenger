from pprint import pprint


class TestSaiGenericProgrammable:
    # object with no parents

    def test_generic_programmable_create(self, npu):
        commands = [
            {
                'name': 'generic_programmable_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_GENERIC_PROGRAMMABLE',
                'attributes': ['SAI_GENERIC_PROGRAMMABLE_ATTR_OBJECT_NAME', '2:10,11'],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_generic_programmable_remove(self, npu):
        commands = [{'name': 'generic_programmable_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

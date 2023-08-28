from pprint import pprint


class TestSaiArs:
    # object with no attributes

    def test_ars_create(self, npu):
        commands = [
            {
                'name': 'ars_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ARS',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_ars_remove(self, npu):
        commands = [{'name': 'ars_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

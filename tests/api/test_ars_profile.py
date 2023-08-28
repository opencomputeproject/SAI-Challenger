from pprint import pprint


class TestSaiArsProfile:
    # object with no attributes

    def test_ars_profile_create(self, npu):
        commands = [
            {
                'name': 'ars_profile_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ARS_PROFILE',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_ars_profile_remove(self, npu):
        commands = [{'name': 'ars_profile_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

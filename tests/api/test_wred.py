from pprint import pprint

import pytest


class TestSaiWred:
    # object with no attributes

    @pytest.mark.dependency(scope='session')
    def test_wred_create(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_WRED',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_wred_remove(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_WRED',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

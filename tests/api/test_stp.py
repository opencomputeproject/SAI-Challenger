from pprint import pprint

import pytest


class TestSaiStp:
    # object with no attributes

    @pytest.mark.dependency(scope='session')
    def test_stp_create(self, npu):
        commands = [
            {
                'name': 'stp_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_STP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_stp_remove(self, npu):
        commands = [
            {
                'name': 'stp_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_STP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

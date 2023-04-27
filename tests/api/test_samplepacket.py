from pprint import pprint

import pytest


class TestSaiSamplepacket:
    # object with no parents

    @pytest.mark.dependency(scope='session')
    def test_samplepacket_create(self, npu):
        commands = [
            {
                'name': 'samplepacket_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_SAMPLEPACKET',
                'attributes': ['SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE', '10'],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_samplepacket_remove(self, npu):
        commands = [
            {
                'name': 'samplepacket_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_SAMPLEPACKET',
                'attributes': ['SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE', '10'],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

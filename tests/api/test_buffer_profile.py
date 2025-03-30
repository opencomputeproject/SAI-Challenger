from pprint import pprint

import pytest


@pytest.fixture(scope='module', autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for {} testbed'.format(testbed.name))


@pytest.mark.npu
class TestSaiBufferProfile:
    # object with parent SAI_OBJECT_TYPE_BUFFER_POOL

    def test_buffer_profile_create(self, npu):
        commands = [
            {
                'name': 'buffer_pool_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_BUFFER_POOL',
                'attributes': [
                    'SAI_BUFFER_POOL_ATTR_TYPE',
                    'SAI_BUFFER_POOL_TYPE_INGRESS',
                    'SAI_BUFFER_POOL_ATTR_SIZE',
                    '10',
                ],
            },
            {
                'name': 'buffer_profile_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_BUFFER_PROFILE',
                'attributes': [
                    'SAI_BUFFER_PROFILE_ATTR_POOL_ID',
                    '$buffer_pool_1',
                    'SAI_BUFFER_PROFILE_ATTR_RESERVED_BUFFER_SIZE',
                    '10',
                    'SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE',
                    'SAI_BUFFER_PROFILE_THRESHOLD_MODE_STATIC',
                    'SAI_BUFFER_PROFILE_ATTR_SHARED_DYNAMIC_TH',
                    '1',
                    'SAI_BUFFER_PROFILE_ATTR_SHARED_STATIC_TH',
                    '10',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

from pprint import pprint

import pytest


class TestSaiAclRange:
    # object with no parents

    @pytest.mark.dependency(scope='session')
    def test_acl_range_create(self, npu):
        commands = [
            {
                'name': 'acl_range_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_RANGE',
                'attributes': [
                    'SAI_ACL_RANGE_ATTR_TYPE',
                    'SAI_ACL_RANGE_TYPE_L4_SRC_PORT_RANGE',
                    'SAI_ACL_RANGE_ATTR_LIMIT',
                    '10,20',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_acl_range_remove(self, npu):
        commands = [
            {
                'name': 'acl_range_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_ACL_RANGE',
                'attributes': [
                    'SAI_ACL_RANGE_ATTR_TYPE',
                    'SAI_ACL_RANGE_TYPE_L4_SRC_PORT_RANGE',
                    'SAI_ACL_RANGE_ATTR_LIMIT',
                    '10,20',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

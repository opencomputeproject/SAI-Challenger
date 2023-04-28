from pprint import pprint

import pytest


class TestSaiAclTableGroupMember:
    # object with parent SAI_OBJECT_TYPE_ACL_TABLE_GROUP SAI_OBJECT_TYPE_ACL_TABLE

    @pytest.mark.dependency(scope='session')
    def test_acl_table_group_member_create(self, npu):
        commands = [
            {
                'name': 'acl_table_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE_GROUP',
                'attributes': [
                    'SAI_ACL_TABLE_GROUP_ATTR_ACL_STAGE',
                    'SAI_ACL_STAGE_INGRESS',
                ],
            },
            {
                'name': 'acl_table_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE',
                'attributes': ['SAI_ACL_TABLE_ATTR_ACL_STAGE', 'SAI_ACL_STAGE_INGRESS'],
            },
            {
                'name': 'acl_table_group_member_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE_GROUP_MEMBER',
                'attributes': [
                    'SAI_ACL_TABLE_GROUP_MEMBER_ATTR_ACL_TABLE_GROUP_ID',
                    '$acl_table_group_1',
                    'SAI_ACL_TABLE_GROUP_MEMBER_ATTR_ACL_TABLE_ID',
                    '$acl_table_1',
                    'SAI_ACL_TABLE_GROUP_MEMBER_ATTR_PRIORITY',
                    '10',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_acl_table_group_member_remove(self, npu):
        commands = [
            {
                'name': 'acl_table_group_member_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE_GROUP_MEMBER',
                'attributes': [
                    'SAI_ACL_TABLE_GROUP_MEMBER_ATTR_ACL_TABLE_GROUP_ID',
                    '$acl_table_group_1',
                    'SAI_ACL_TABLE_GROUP_MEMBER_ATTR_ACL_TABLE_ID',
                    '$acl_table_1',
                    'SAI_ACL_TABLE_GROUP_MEMBER_ATTR_PRIORITY',
                    '10',
                ],
            },
            {
                'name': 'acl_table_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE',
                'attributes': ['SAI_ACL_TABLE_ATTR_ACL_STAGE', 'SAI_ACL_STAGE_INGRESS'],
            },
            {
                'name': 'acl_table_group_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE_GROUP',
                'attributes': [
                    'SAI_ACL_TABLE_GROUP_ATTR_ACL_STAGE',
                    'SAI_ACL_STAGE_INGRESS',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

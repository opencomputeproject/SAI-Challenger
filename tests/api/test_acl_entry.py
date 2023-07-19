from pprint import pprint


class TestSaiAclEntry:
    # object with parent SAI_OBJECT_TYPE_ACL_TABLE

    def test_acl_entry_create(self, npu):
        commands = [
            {
                'name': 'acl_table_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE',
                'attributes': ['SAI_ACL_TABLE_ATTR_ACL_STAGE', 'SAI_ACL_STAGE_INGRESS'],
            },
            {
                'name': 'acl_entry_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_ENTRY',
                'attributes': ['SAI_ACL_ENTRY_ATTR_TABLE_ID', '$acl_table_1'],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_acl_entry_remove(self, npu):
        commands = [
            {
                'name': 'acl_entry_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_ACL_ENTRY',
                'attributes': ['SAI_ACL_ENTRY_ATTR_TABLE_ID', '$acl_table_1'],
            },
            {
                'name': 'acl_table_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE',
                'attributes': ['SAI_ACL_TABLE_ATTR_ACL_STAGE', 'SAI_ACL_STAGE_INGRESS'],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

from pprint import pprint

class TestSaiAclCounter:
    # object with parent SAI_OBJECT_TYPE_ACL_TABLE

    def test_acl_counter_create(self, npu):
        commands = [
            {
                'name': 'acl_table_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_TABLE',
                'attributes': ['SAI_ACL_TABLE_ATTR_ACL_STAGE', 'SAI_ACL_STAGE_INGRESS'],
            },
            {
                'name': 'acl_counter_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ACL_COUNTER',
                'attributes': ['SAI_ACL_COUNTER_ATTR_TABLE_ID', '$acl_table_1'],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)


    @pytest.mark.dependency(name="test_sai_acl_counter_attr_label_set")
    def test_sai_acl_counter_attr_label_set(self, npu):

        commands = [
            {
                "name": "acl_counter_1",
                "op": "set",
                "attributes": ["SAI_ACL_COUNTER_ATTR_LABEL", '""']
            }
        ]
        npu.objects_discovery()
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)


    def test_acl_counter_remove(self, npu):
        commands = [
            {
                'name': 'acl_counter_1',
                'op': 'remove',
            },
            {
                'name': 'acl_table_1',
                'op': 'remove',
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

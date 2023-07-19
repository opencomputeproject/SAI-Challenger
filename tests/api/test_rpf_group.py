from pprint import pprint


class TestSaiRpfGroup:
    # object with no attributes

    def test_rpf_group_create(self, npu):
        commands = [
            {
                'name': 'rpf_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_RPF_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_rpf_group_remove(self, npu):
        commands = [
            {
                'name': 'rpf_group_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_RPF_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

from pprint import pprint


class TestSaiNextHopGroup:
    # object with no parents

    def test_next_hop_group_create(self, npu):
        commands = [
            {
                'name': 'next_hop_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_NEXT_HOP_GROUP',
                'attributes': [
                    'SAI_NEXT_HOP_GROUP_ATTR_TYPE',
                    'SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_UNORDERED_ECMP',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_next_hop_group_remove(self, npu):
        commands = [
            {
                'name': 'next_hop_group_1',
                'op': 'remove',
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

from pprint import pprint


class TestSaiNextHopGroupMap:
    # object with no parents

    def test_next_hop_group_map_create(self, npu):
        commands = [
            {
                'name': 'next_hop_group_map_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MAP',
                'attributes': [
                    'SAI_NEXT_HOP_GROUP_MAP_ATTR_TYPE',
                    'SAI_NEXT_HOP_GROUP_MAP_TYPE_FORWARDING_CLASS_TO_INDEX',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_next_hop_group_map_remove(self, npu):
        commands = [{'name': 'next_hop_group_map_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

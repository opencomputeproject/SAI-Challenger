from pprint import pprint


class TestSaiHostifTrapGroup:
    # object with no attributes

    def test_hostif_trap_group_create(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_hostif_trap_group_remove(self, npu):
        commands = [
            {
                'name': 'hostif_trap_group_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

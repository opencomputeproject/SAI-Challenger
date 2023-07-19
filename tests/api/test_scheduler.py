from pprint import pprint


class TestSaiScheduler:
    # object with no attributes

    def test_scheduler_create(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_SCHEDULER',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_scheduler_remove(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_SCHEDULER',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

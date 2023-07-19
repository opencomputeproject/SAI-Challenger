from pprint import pprint


class TestSaiLag:
    # object with no attributes

    def test_lag_create(self, npu):
        commands = [
            {
                'name': 'lag_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_LAG',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_lag_remove(self, npu):
        commands = [
            {
                'name': 'lag_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_LAG',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

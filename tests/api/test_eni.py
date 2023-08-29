from pprint import pprint


class TestSaiEni:
    # object with no attributes

    def test_eni_create(self, npu):
        commands = [
            {
                'name': 'eni_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ENI',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_eni_remove(self, npu):
        commands = [{'name': 'eni_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

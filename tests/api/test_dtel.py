from pprint import pprint


class TestSaiDtel:
    # object with no attributes

    def test_dtel_create(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DTEL',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_dtel_remove(self, npu):
        commands = [{'name': 'dtel_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

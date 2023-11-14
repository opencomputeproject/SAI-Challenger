from pprint import pprint


class TestSaiDtelIntSession:
    # object with no attributes

    def test_dtel_int_session_create(self, npu):
        commands = [
            {
                'name': 'dtel_int_session_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DTEL_INT_SESSION',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_dtel_int_session_remove(self, npu):
        commands = [{'name': 'dtel_int_session_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

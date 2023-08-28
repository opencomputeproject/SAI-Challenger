from pprint import pprint


class TestSaiDtelEvent:
    # object with no parents

    def test_dtel_event_create(self, npu):
        commands = [
            {
                'name': 'dtel_event_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DTEL_EVENT',
                'attributes': [
                    'SAI_DTEL_EVENT_ATTR_TYPE',
                    'SAI_DTEL_EVENT_TYPE_FLOW_STATE',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_dtel_event_remove(self, npu):
        commands = [{'name': 'dtel_event_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

from pprint import pprint


class TestSaiTamCollector:
    # object with parent SAI_OBJECT_TYPE_TAM_TRANSPORT

    def test_tam_collector_create(self, npu):
        commands = [
            {
                'name': 'tam_transport_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_TAM_TRANSPORT',
                'attributes': [
                    'SAI_TAM_TRANSPORT_ATTR_TRANSPORT_TYPE',
                    'SAI_TAM_TRANSPORT_TYPE_TCP',
                ],
            },
            {
                'name': 'tam_collector_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_TAM_COLLECTOR',
                'attributes': [
                    'SAI_TAM_COLLECTOR_ATTR_SRC_IP',
                    '180.0.0.1',
                    'SAI_TAM_COLLECTOR_ATTR_DST_IP',
                    '180.0.0.1',
                    'SAI_TAM_COLLECTOR_ATTR_TRANSPORT',
                    '$tam_transport_1',
                    'SAI_TAM_COLLECTOR_ATTR_DSCP_VALUE',
                    '1',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_tam_collector_remove(self, npu):
        commands = [
            {'name': 'tam_collector_1', 'op': 'remove'},
            {'name': 'tam_transport_1', 'op': 'remove'},
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

from pprint import pprint


class TestSaiMacsec:
    # object with no parents

    def test_macsec_create(self, npu):
        commands = [
            {
                'name': 'macsec_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_MACSEC',
                'attributes': [
                    'SAI_MACSEC_ATTR_DIRECTION',
                    'SAI_MACSEC_DIRECTION_EGRESS',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_macsec_remove(self, npu):
        commands = [{'name': 'macsec_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

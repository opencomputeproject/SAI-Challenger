from pprint import pprint


class TestSaiPolicer:
    # object with no parents

    def test_policer_create(self, npu):
        commands = [
            {
                'name': 'policer_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_POLICER',
                'attributes': [
                    'SAI_POLICER_ATTR_METER_TYPE',
                    'SAI_METER_TYPE_PACKETS',
                    'SAI_POLICER_ATTR_MODE',
                    'SAI_POLICER_MODE_SR_TCM',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_policer_remove(self, npu):
        commands = [
            {
                'name': 'policer_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_POLICER',
                'attributes': [
                    'SAI_POLICER_ATTR_METER_TYPE',
                    'SAI_METER_TYPE_PACKETS',
                    'SAI_POLICER_ATTR_MODE',
                    'SAI_POLICER_MODE_SR_TCM',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

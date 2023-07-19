from pprint import pprint


class TestSaiIpmcGroup:
    # object with no attributes

    def test_ipmc_group_create(self, npu):
        commands = [
            {
                'name': 'ipmc_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_IPMC_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_ipmc_group_remove(self, npu):
        commands = [
            {
                'name': 'ipmc_group_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_IPMC_GROUP',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

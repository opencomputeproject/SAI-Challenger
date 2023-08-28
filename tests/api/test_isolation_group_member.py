from pprint import pprint


class TestSaiIsolationGroupMember:
    # object with parent SAI_OBJECT_TYPE_ISOLATION_GROUP SAI_OBJECT_TYPE_PORT SAI_OBJECT_TYPE_BRIDGE_PORT

    def test_isolation_group_member_create(self, npu):
        commands = [
            {
                'name': 'isolation_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ISOLATION_GROUP',
                'attributes': [
                    'SAI_ISOLATION_GROUP_ATTR_TYPE',
                    'SAI_ISOLATION_GROUP_TYPE_PORT',
                ],
            },
            {
                'name': 'port_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_PORT',
                'attributes': [
                    'SAI_PORT_ATTR_HW_LANE_LIST',
                    '2:10,11',
                    'SAI_PORT_ATTR_SPEED',
                    '10',
                ],
            },
            {
                'name': 'isolation_group_member_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_ISOLATION_GROUP_MEMBER',
                'attributes': [
                    'SAI_ISOLATION_GROUP_MEMBER_ATTR_ISOLATION_GROUP_ID',
                    '$isolation_group_1',
                    'SAI_ISOLATION_GROUP_MEMBER_ATTR_ISOLATION_OBJECT',
                    '$port_1',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_isolation_group_member_remove(self, npu):
        commands = [
            {'name': 'isolation_group_member_1', 'op': 'remove'},
            {'name': 'isolation_group_1', 'op': 'remove'},
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

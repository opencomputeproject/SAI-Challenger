from pprint import pprint


class TestSaiSwitchTunnel:
    # object with no parents

    def test_switch_tunnel_create(self, npu):
        commands = [
            {
                'name': 'switch_tunnel_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_SWITCH_TUNNEL',
                'attributes': [
                    'SAI_SWITCH_TUNNEL_ATTR_TUNNEL_TYPE',
                    'SAI_TUNNEL_TYPE_IPINIP',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_switch_tunnel_remove(self, npu):
        commands = [{'name': 'switch_tunnel_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

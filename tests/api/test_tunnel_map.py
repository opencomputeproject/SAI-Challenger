from pprint import pprint

import pytest


class TestSaiTunnelMap:
    # object with no parents

    @pytest.mark.dependency(scope='session')
    def test_tunnel_map_create(self, npu):
        commands = [
            {
                'name': 'tunnel_map_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_TUNNEL_MAP',
                'attributes': [
                    'SAI_TUNNEL_MAP_ATTR_TYPE',
                    'SAI_TUNNEL_MAP_TYPE_OECN_TO_UECN',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)
        assert all(results), 'Create error'

    def test_tunnel_map_remove(self, npu):
        commands = [
            {
                'name': 'tunnel_map_1',
                'op': 'remove',
                'type': 'SAI_OBJECT_TYPE_TUNNEL_MAP',
                'attributes': [
                    'SAI_TUNNEL_MAP_ATTR_TYPE',
                    'SAI_TUNNEL_MAP_TYPE_OECN_TO_UECN',
                ],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
        assert all(
            [result == 'SAI_STATUS_SUCCESS' for result in results]
        ), 'Remove error'

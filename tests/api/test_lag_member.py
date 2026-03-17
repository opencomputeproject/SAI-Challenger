from pprint import pprint

import pytest


@pytest.fixture(scope='module', autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for {} testbed'.format(testbed.name))


@pytest.mark.npu
class TestSaiLagMember:
    # object with parent SAI_OBJECT_TYPE_LAG SAI_OBJECT_TYPE_PORT SAI_OBJECT_TYPE_SYSTEM_PORT

    def test_lag_member_create(self, npu):
        commands = [
            {
                'name': 'lag_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_LAG',
                'attributes': [],
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
                'name': 'lag_member_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_LAG_MEMBER',
                'attributes': [
                    'SAI_LAG_MEMBER_ATTR_LAG_ID',
                    '$lag_1',
                    'SAI_LAG_MEMBER_ATTR_PORT_ID',
                    '$port_1',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_lag_member_attr_egress_disable_set')
    def test_sai_lag_member_attr_egress_disable_set(self, npu):
        commands = [
            {
                'name': 'lag_member_1',
                'op': 'set',
                'attributes': ['SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)


    @pytest.mark.dependency(name='test_sai_lag_member_attr_ingress_disable_set')
    def test_sai_lag_member_attr_ingress_disable_set(self, npu):
        commands = [
            {
                'name': 'lag_member_1',
                'op': 'set',
                'attributes': ['SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)


    def test_lag_member_remove(self, npu):
        commands = [
            {'name': 'lag_member_1', 'op': 'remove'},
            {'name': 'port_1', 'op': 'remove'},
            {'name': 'lag_1', 'op': 'remove'},
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

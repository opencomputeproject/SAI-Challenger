from pprint import pprint

import pytest


@pytest.fixture(scope='module', autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for {} testbed'.format(testbed.name))


@pytest.mark.npu
class TestSaiDtel:
    # object with no attributes

    def test_dtel_create(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DTEL',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_dtel_attr_postcard_enable_set')
    def test_sai_dtel_attr_postcard_enable_set(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'set',
                'attributes': ['SAI_DTEL_ATTR_POSTCARD_ENABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_dtel_attr_postcard_enable_set'])
    def test_sai_dtel_attr_postcard_enable_get(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'get',
                'attributes': ['SAI_DTEL_ATTR_POSTCARD_ENABLE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'false', 'Get error, expected false but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_dtel_attr_drop_report_enable_set')
    def test_sai_dtel_attr_drop_report_enable_set(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'set',
                'attributes': ['SAI_DTEL_ATTR_DROP_REPORT_ENABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_dtel_attr_drop_report_enable_set'])
    def test_sai_dtel_attr_drop_report_enable_get(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'get',
                'attributes': ['SAI_DTEL_ATTR_DROP_REPORT_ENABLE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'false', 'Get error, expected false but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_dtel_attr_queue_report_enable_set')
    def test_sai_dtel_attr_queue_report_enable_set(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'set',
                'attributes': ['SAI_DTEL_ATTR_QUEUE_REPORT_ENABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_dtel_attr_queue_report_enable_set'])
    def test_sai_dtel_attr_queue_report_enable_get(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'get',
                'attributes': ['SAI_DTEL_ATTR_QUEUE_REPORT_ENABLE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'false', 'Get error, expected false but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_dtel_attr_switch_id_set')
    def test_sai_dtel_attr_switch_id_set(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'set',
                'attributes': ['SAI_DTEL_ATTR_SWITCH_ID', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_dtel_attr_switch_id_set'])
    def test_sai_dtel_attr_switch_id_get(self, npu):
        commands = [
            {'name': 'dtel_1', 'op': 'get', 'attributes': ['SAI_DTEL_ATTR_SWITCH_ID']}
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_dtel_attr_flow_state_clear_cycle_set')
    def test_sai_dtel_attr_flow_state_clear_cycle_set(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'set',
                'attributes': ['SAI_DTEL_ATTR_FLOW_STATE_CLEAR_CYCLE', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_dtel_attr_flow_state_clear_cycle_set'])
    def test_sai_dtel_attr_flow_state_clear_cycle_get(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'get',
                'attributes': ['SAI_DTEL_ATTR_FLOW_STATE_CLEAR_CYCLE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_dtel_attr_latency_sensitivity_set')
    def test_sai_dtel_attr_latency_sensitivity_set(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'set',
                'attributes': ['SAI_DTEL_ATTR_LATENCY_SENSITIVITY', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_dtel_attr_latency_sensitivity_set'])
    def test_sai_dtel_attr_latency_sensitivity_get(self, npu):
        commands = [
            {
                'name': 'dtel_1',
                'op': 'get',
                'attributes': ['SAI_DTEL_ATTR_LATENCY_SENSITIVITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' % r_value

    def test_dtel_remove(self, npu):
        commands = [{'name': 'dtel_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

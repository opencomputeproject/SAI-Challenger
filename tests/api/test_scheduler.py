from pprint import pprint

import pytest


@pytest.fixture(scope="module", autouse=True)
def discovery(npu):
    npu.objects_discovery()


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for {} testbed".format(testbed.name))


class TestSaiScheduler:
    # object with no attributes

    def test_scheduler_create(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_SCHEDULER',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_scheduler_attr_scheduling_type_set')
    def test_sai_scheduler_attr_scheduling_type_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': [
                    'SAI_SCHEDULER_ATTR_SCHEDULING_TYPE',
                    'SAI_SCHEDULING_TYPE_WRR',
                ],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_scheduler_attr_scheduling_type_set'])
    def test_sai_scheduler_attr_scheduling_type_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_SCHEDULING_TYPE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_SCHEDULING_TYPE_WRR', (
            'Get error, expected SAI_SCHEDULING_TYPE_WRR but got %s' % r_value
        )

    @pytest.mark.dependency(name='test_sai_scheduler_attr_scheduling_weight_set')
    def test_sai_scheduler_attr_scheduling_weight_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': ['SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT', '1'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_scheduler_attr_scheduling_weight_set'])
    def test_sai_scheduler_attr_scheduling_weight_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '1', 'Get error, expected 1 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_scheduler_attr_meter_type_set')
    def test_sai_scheduler_attr_meter_type_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': ['SAI_SCHEDULER_ATTR_METER_TYPE', 'SAI_METER_TYPE_BYTES'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_scheduler_attr_meter_type_set'])
    def test_sai_scheduler_attr_meter_type_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_METER_TYPE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_METER_TYPE_BYTES', (
            'Get error, expected SAI_METER_TYPE_BYTES but got %s' % r_value
        )

    @pytest.mark.dependency(name='test_sai_scheduler_attr_min_bandwidth_rate_set')
    def test_sai_scheduler_attr_min_bandwidth_rate_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': ['SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_scheduler_attr_min_bandwidth_rate_set'])
    def test_sai_scheduler_attr_min_bandwidth_rate_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE'],
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

    @pytest.mark.dependency(name='test_sai_scheduler_attr_min_bandwidth_burst_rate_set')
    def test_sai_scheduler_attr_min_bandwidth_burst_rate_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': ['SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_BURST_RATE', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(
        depends=['test_sai_scheduler_attr_min_bandwidth_burst_rate_set']
    )
    def test_sai_scheduler_attr_min_bandwidth_burst_rate_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_BURST_RATE'],
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

    @pytest.mark.dependency(name='test_sai_scheduler_attr_max_bandwidth_rate_set')
    def test_sai_scheduler_attr_max_bandwidth_rate_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': ['SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_scheduler_attr_max_bandwidth_rate_set'])
    def test_sai_scheduler_attr_max_bandwidth_rate_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE'],
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

    @pytest.mark.dependency(name='test_sai_scheduler_attr_max_bandwidth_burst_rate_set')
    def test_sai_scheduler_attr_max_bandwidth_burst_rate_set(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'set',
                'attributes': ['SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_BURST_RATE', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(
        depends=['test_sai_scheduler_attr_max_bandwidth_burst_rate_set']
    )
    def test_sai_scheduler_attr_max_bandwidth_burst_rate_get(self, npu):
        commands = [
            {
                'name': 'scheduler_1',
                'op': 'get',
                'attributes': ['SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_BURST_RATE'],
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

    def test_scheduler_remove(self, npu):
        commands = [{'name': 'scheduler_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

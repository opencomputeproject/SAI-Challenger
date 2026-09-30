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


class TestSaiWred:
    # object with no attributes

    def test_wred_create(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_WRED',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_wred_attr_green_enable_set')
    def test_sai_wred_attr_green_enable_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_GREEN_ENABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_green_enable_set'])
    def test_sai_wred_attr_green_enable_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_GREEN_ENABLE'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_green_min_threshold_set')
    def test_sai_wred_attr_green_min_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_GREEN_MIN_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_green_min_threshold_set'])
    def test_sai_wred_attr_green_min_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_GREEN_MIN_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_green_max_threshold_set')
    def test_sai_wred_attr_green_max_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_GREEN_MAX_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_green_max_threshold_set'])
    def test_sai_wred_attr_green_max_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_GREEN_MAX_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_green_drop_probability_set')
    def test_sai_wred_attr_green_drop_probability_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_GREEN_DROP_PROBABILITY', '100'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_green_drop_probability_set'])
    def test_sai_wred_attr_green_drop_probability_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_GREEN_DROP_PROBABILITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '100', 'Get error, expected 100 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_yellow_enable_set')
    def test_sai_wred_attr_yellow_enable_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_YELLOW_ENABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_yellow_enable_set'])
    def test_sai_wred_attr_yellow_enable_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_YELLOW_ENABLE'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_yellow_min_threshold_set')
    def test_sai_wred_attr_yellow_min_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_YELLOW_MIN_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_yellow_min_threshold_set'])
    def test_sai_wred_attr_yellow_min_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_YELLOW_MIN_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_yellow_max_threshold_set')
    def test_sai_wred_attr_yellow_max_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_YELLOW_MAX_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_yellow_max_threshold_set'])
    def test_sai_wred_attr_yellow_max_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_YELLOW_MAX_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_yellow_drop_probability_set')
    def test_sai_wred_attr_yellow_drop_probability_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_YELLOW_DROP_PROBABILITY', '100'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_yellow_drop_probability_set'])
    def test_sai_wred_attr_yellow_drop_probability_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_YELLOW_DROP_PROBABILITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '100', 'Get error, expected 100 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_red_enable_set')
    def test_sai_wred_attr_red_enable_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_RED_ENABLE', 'false'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_red_enable_set'])
    def test_sai_wred_attr_red_enable_get(self, npu):
        commands = [
            {'name': 'wred_1', 'op': 'get', 'attributes': ['SAI_WRED_ATTR_RED_ENABLE']}
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'false', 'Get error, expected false but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_red_min_threshold_set')
    def test_sai_wred_attr_red_min_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_RED_MIN_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_red_min_threshold_set'])
    def test_sai_wred_attr_red_min_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_RED_MIN_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_red_max_threshold_set')
    def test_sai_wred_attr_red_max_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_RED_MAX_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_red_max_threshold_set'])
    def test_sai_wred_attr_red_max_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_RED_MAX_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_red_drop_probability_set')
    def test_sai_wred_attr_red_drop_probability_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_RED_DROP_PROBABILITY', '100'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_red_drop_probability_set'])
    def test_sai_wred_attr_red_drop_probability_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_RED_DROP_PROBABILITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '100', 'Get error, expected 100 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_weight_set')
    def test_sai_wred_attr_weight_set(self, npu):
        commands = [
            {'name': 'wred_1', 'op': 'set', 'attributes': ['SAI_WRED_ATTR_WEIGHT', '0']}
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_weight_set'])
    def test_sai_wred_attr_weight_get(self, npu):
        commands = [
            {'name': 'wred_1', 'op': 'get', 'attributes': ['SAI_WRED_ATTR_WEIGHT']}
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_mark_mode_set')
    def test_sai_wred_attr_ecn_mark_mode_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_MARK_MODE', 'SAI_ECN_MARK_MODE_NONE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_mark_mode_set'])
    def test_sai_wred_attr_ecn_mark_mode_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_MARK_MODE'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_ECN_MARK_MODE_NONE', (
            'Get error, expected SAI_ECN_MARK_MODE_NONE but got %s' % r_value
        )

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_green_min_threshold_set')
    def test_sai_wred_attr_ecn_green_min_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_GREEN_MIN_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_green_min_threshold_set'])
    def test_sai_wred_attr_ecn_green_min_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_GREEN_MIN_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_green_max_threshold_set')
    def test_sai_wred_attr_ecn_green_max_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_GREEN_MAX_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_green_max_threshold_set'])
    def test_sai_wred_attr_ecn_green_max_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_GREEN_MAX_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_green_mark_probability_set')
    def test_sai_wred_attr_ecn_green_mark_probability_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_GREEN_MARK_PROBABILITY', '100'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(
        depends=['test_sai_wred_attr_ecn_green_mark_probability_set']
    )
    def test_sai_wred_attr_ecn_green_mark_probability_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_GREEN_MARK_PROBABILITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '100', 'Get error, expected 100 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_yellow_min_threshold_set')
    def test_sai_wred_attr_ecn_yellow_min_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_YELLOW_MIN_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_yellow_min_threshold_set'])
    def test_sai_wred_attr_ecn_yellow_min_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_YELLOW_MIN_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_yellow_max_threshold_set')
    def test_sai_wred_attr_ecn_yellow_max_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_YELLOW_MAX_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_yellow_max_threshold_set'])
    def test_sai_wred_attr_ecn_yellow_max_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_YELLOW_MAX_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_yellow_mark_probability_set')
    def test_sai_wred_attr_ecn_yellow_mark_probability_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_YELLOW_MARK_PROBABILITY', '100'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(
        depends=['test_sai_wred_attr_ecn_yellow_mark_probability_set']
    )
    def test_sai_wred_attr_ecn_yellow_mark_probability_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_YELLOW_MARK_PROBABILITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '100', 'Get error, expected 100 but got %s' % r_value

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_red_min_threshold_set')
    def test_sai_wred_attr_ecn_red_min_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_RED_MIN_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_red_min_threshold_set'])
    def test_sai_wred_attr_ecn_red_min_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_RED_MIN_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_red_max_threshold_set')
    def test_sai_wred_attr_ecn_red_max_threshold_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_RED_MAX_THRESHOLD', '0'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_red_max_threshold_set'])
    def test_sai_wred_attr_ecn_red_max_threshold_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_RED_MAX_THRESHOLD'],
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

    @pytest.mark.dependency(name='test_sai_wred_attr_ecn_red_mark_probability_set')
    def test_sai_wred_attr_ecn_red_mark_probability_set(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'set',
                'attributes': ['SAI_WRED_ATTR_ECN_RED_MARK_PROBABILITY', '100'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        pprint(results)

    @pytest.mark.dependency(depends=['test_sai_wred_attr_ecn_red_mark_probability_set'])
    def test_sai_wred_attr_ecn_red_mark_probability_get(self, npu):
        commands = [
            {
                'name': 'wred_1',
                'op': 'get',
                'attributes': ['SAI_WRED_ATTR_ECN_RED_MARK_PROBABILITY'],
            }
        ]
        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values get =======')
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '100', 'Get error, expected 100 but got %s' % r_value

    def test_wred_remove(self, npu):
        commands = [{'name': 'wred_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

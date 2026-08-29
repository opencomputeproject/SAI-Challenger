
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


@pytest.mark.npu
class TestSaiPolicer:
    # object with no parents

    def test_policer_create(self, npu):

        commands = [{'name': 'policer_1', 'op': 'create', 'type': 'SAI_OBJECT_TYPE_POLICER', 'attributes': ['SAI_POLICER_ATTR_METER_TYPE', 'SAI_METER_TYPE_PACKETS', 'SAI_POLICER_ATTR_MODE', 'SAI_POLICER_MODE_SR_TCM']}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_policer_attr_cbs_set")
    def test_sai_policer_attr_cbs_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_CBS", '0']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_cbs_set"])
    def test_sai_policer_attr_cbs_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_CBS"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' %  r_value


    @pytest.mark.dependency(name="test_sai_policer_attr_cir_set")
    def test_sai_policer_attr_cir_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_CIR", '0']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_cir_set"])
    def test_sai_policer_attr_cir_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_CIR"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' %  r_value


    @pytest.mark.dependency(name="test_sai_policer_attr_pbs_set")
    def test_sai_policer_attr_pbs_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_PBS", '0']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_pbs_set"])
    def test_sai_policer_attr_pbs_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_PBS"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' %  r_value


    @pytest.mark.dependency(name="test_sai_policer_attr_pir_set")
    def test_sai_policer_attr_pir_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_PIR", '0']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_pir_set"])
    def test_sai_policer_attr_pir_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_PIR"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == '0', 'Get error, expected 0 but got %s' %  r_value


    @pytest.mark.dependency(name="test_sai_policer_attr_green_packet_action_set")
    def test_sai_policer_attr_green_packet_action_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_GREEN_PACKET_ACTION", 'SAI_PACKET_ACTION_FORWARD']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_green_packet_action_set"])
    def test_sai_policer_attr_green_packet_action_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_GREEN_PACKET_ACTION"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_PACKET_ACTION_FORWARD', 'Get error, expected SAI_PACKET_ACTION_FORWARD but got %s' %  r_value


    @pytest.mark.dependency(name="test_sai_policer_attr_yellow_packet_action_set")
    def test_sai_policer_attr_yellow_packet_action_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_YELLOW_PACKET_ACTION", 'SAI_PACKET_ACTION_FORWARD']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_yellow_packet_action_set"])
    def test_sai_policer_attr_yellow_packet_action_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_YELLOW_PACKET_ACTION"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_PACKET_ACTION_FORWARD', 'Get error, expected SAI_PACKET_ACTION_FORWARD but got %s' %  r_value


    @pytest.mark.dependency(name="test_sai_policer_attr_red_packet_action_set")
    def test_sai_policer_attr_red_packet_action_set(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "set",
                "attributes": ["SAI_POLICER_ATTR_RED_PACKET_ACTION", 'SAI_PACKET_ACTION_FORWARD']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_policer_attr_red_packet_action_set"])
    def test_sai_policer_attr_red_packet_action_get(self, npu):

        commands = [
            {
                "name": "policer_1",
                "op": "get",
                "attributes": ["SAI_POLICER_ATTR_RED_PACKET_ACTION"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_PACKET_ACTION_FORWARD', 'Get error, expected SAI_PACKET_ACTION_FORWARD but got %s' %  r_value


    def test_policer_remove(self, npu):

        commands = [{'name': 'policer_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


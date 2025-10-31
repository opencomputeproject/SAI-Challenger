from pprint import pprint

import pytest


@pytest.fixture(scope='module', autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for {} testbed'.format(testbed.name))


@pytest.mark.npu
class TestSaiMyMac:
    # object with no attributes

    def test_my_mac_create(self, npu):
        commands = [
            {
                'name': 'my_mac_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_MY_MAC',
                'attributes': [],
            }
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    def test_my_mac_remove(self, npu):
        commands = [{'name': 'my_mac_1', 'op': 'remove'}]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

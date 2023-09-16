from pprint import pprint

import pytest

@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.dpu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

@pytest.mark.dpu
class TestSaiDashAclRule:
    # object with parent SAI_OBJECT_TYPE_DASH_ACL_GROUP

    def test_dash_acl_rule_create(self, dpu):
        commands = [
            {
                'name': 'dash_acl_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DASH_ACL_GROUP',
                'attributes': ['SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY', 'SAI_IP_ADDR_FAMILY_IPV4',],
            },
            {
                'name': 'dash_acl_rule_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_DASH_ACL_RULE',
                'attributes': [
                    'SAI_DASH_ACL_RULE_ATTR_DASH_ACL_GROUP_ID','$dash_acl_group_1',
                    'SAI_DASH_ACL_RULE_ATTR_DIP','1.1.1.1',
                    'SAI_DASH_ACL_RULE_ATTR_SIP','2.2.2.2',
                    'SAI_DASH_ACL_RULE_ATTR_PROTOCOL','17',
                    'SAI_DASH_ACL_RULE_ATTR_SRC_PORT','5678',
                    'SAI_DASH_ACL_RULE_ATTR_DST_PORT','8765',
                    'SAI_DASH_ACL_RULE_ATTR_PRIORITY','10',
                ],
            },
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name='test_sai_dash_acl_rule_attr_action_set')
    def test_sai_dash_acl_rule_attr_action_set(self, dpu):
        commands = [
            {
                'name': 'dash_acl_rule_1',
                'op': 'set',
                'attributes': [
                    'SAI_DASH_ACL_RULE_ATTR_ACTION',
                    'SAI_DASH_ACL_RULE_ACTION_PERMIT',
                ],
            }
        ]
        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values set =======')
        pprint(results)


    def test_dash_acl_rule_remove(self, dpu):
        commands = [
            {'name': 'dash_acl_rule_1', 'op': 'remove'},
            {'name': 'dash_acl_group_1', 'op': 'remove'},
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)

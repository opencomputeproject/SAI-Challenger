
from pprint import pprint

import pytest

@pytest.mark.dpu
class TestSaiDashAclGroup:
    # object with no attributes

    def test_dash_acl_group_create(self, dpu):
        #Attribs are not marked mandatory but if we dont gives it throws an error
        commands = [
            {
            'name': 'dash_acl_group_1',
            'op': 'create',
            'type': 'SAI_OBJECT_TYPE_DASH_ACL_GROUP',
            'attributes': ["SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY","SAI_IP_ADDR_FAMILY_IPV4"]
            }
        ]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)



    @pytest.mark.dependency(name="test_sai_dash_acl_group_attr_ip_addr_family_set")
    def test_sai_dash_acl_group_attr_ip_addr_family_set(self, dpu):

        commands = [
            {
                "name": "dash_acl_group_1",
                "op": "set",
                "attributes": ["SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", 'SAI_IP_ADDR_FAMILY_IPV4']
            }
        ]
        results = [*dpu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        pprint(results)



    def test_dash_acl_group_remove(self, dpu):

        commands = [{'name': 'dash_acl_group_1', 'op': 'remove'}]

        results = [*dpu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)


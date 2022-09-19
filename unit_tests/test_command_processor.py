from sai import Sai
from sai_client.sai_thrift_client.sai_thrift_client import SaiThriftClient
from sai_object import SaiObject
from unittest.mock import Mock, patch


def test_command_processor():
    """
        Command processor is a tool for setup appliance SAI configuration. Such configuration could be stored
        in yaml/json configs and fed to Sai by Command processor. This test show simple configuration setup using it.
    """
    with patch.object(SaiThriftClient, 'start_thrift_client', return_value=(Mock(), Mock())):
        sai_client = SaiThriftClient(Mock())
        command_processor = Sai.CommandProcessor(sai_client)
        command_processor.objects_registry['SWITCH_ID'] = {
            "type": SaiObject.Type.SWITCH,
            "oid": 9288674231451648
        }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_vip_entry',
        ) as create_vip_entry_mock:
            command_processor.process_command({
                "name": "vip_entry",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_VIP_ENTRY",
                "key": {
                    "switch_id": "$SWITCH_ID",
                    "vip": "192.168.0.1"
                },
                "attributes": [
                    *("SAI_VIP_ENTRY_ATTR_ACTION", "SAI_VIP_ENTRY_ACTION_ACCEPT")
                ]
            })
            create_vip_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_direction_lookup_entry',
        ) as create_direction_lookup_entry:
            command_processor.process_command({
                "name": "direction_lookup_entry",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_DIRECTION_LOOKUP_ENTRY",
                "key": {
                    "switch_id": "$SWITCH_ID",
                    "vni": "2000"
                },
                "attributes": [
                    *("SAI_DIRECTION_LOOKUP_ENTRY_ATTR_ACTION",
                      "SAI_DIRECTION_LOOKUP_ENTRY_ACTION_SET_OUTBOUND_DIRECTION")]
            })
            create_direction_lookup_entry.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_dash_acl_group',
                return_value=29554872554618881
        ) as create_acl_group_mock_in:
            command_processor.process_command({
                "name": "acl_in_1",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_DASH_ACL_GROUP",
                "attributes": [*("SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4")]
            })
            create_acl_group_mock_in.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_dash_acl_group',
                return_value=29554872554618880
        ) as create_acl_group_mock_out:
            command_processor.process_command({
                "name": "acl_out_1",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_DASH_ACL_GROUP",
                "attributes": [*("SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4")]
            })
            create_acl_group_mock_out.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_vnet',
                return_value=32088147345014784
        ) as create_vnet:
            command_processor.process_command({
                "name": "vnet_1",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_VNET",
                "attributes": [*("SAI_VNET_ATTR_VNI", "2000")]
            })
            create_vnet.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_eni',
                return_value=30680772461461504
        ) as create_eni_mock:
            command_processor.process_command({
                "name": "eni_id",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_ENI",
                "attributes": [
                    *("SAI_ENI_ATTR_CPS", "10000"),
                    *("SAI_ENI_ATTR_PPS", "100000"),
                    *("SAI_ENI_ATTR_FLOWS", "100000"),
                    *("SAI_ENI_ATTR_ADMIN_STATE", "True"),
                    *("SAI_ENI_ATTR_VM_UNDERLAY_DIP", "10.10.2.10"),
                    *("SAI_ENI_ATTR_VM_VNI", "9"),
                    *("SAI_ENI_ATTR_VNET_ID", "$vnet_1"),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE1_DASH_ACL_GROUP_ID", "$acl_in_1"),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE2_DASH_ACL_GROUP_ID", "$acl_in_1"),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE3_DASH_ACL_GROUP_ID", "$acl_in_1"),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE4_DASH_ACL_GROUP_ID", "$acl_in_1"),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE5_DASH_ACL_GROUP_ID", "$acl_in_1"),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE1_DASH_ACL_GROUP_ID", "$acl_out_1"),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE2_DASH_ACL_GROUP_ID", "$acl_out_1"),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE3_DASH_ACL_GROUP_ID", "$acl_out_1"),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE4_DASH_ACL_GROUP_ID", "$acl_out_1"),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE5_DASH_ACL_GROUP_ID", "$acl_out_1"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE1_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE2_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE3_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE4_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE5_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE1_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE2_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE3_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE4_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE5_DASH_ACL_GROUP_ID", "0"),
                ]
            })
            create_eni_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_eni_ether_address_map_entry',
        ) as create_eni_ether_address_map_entry_mock:
            command_processor.process_command({
                "name": "eni_ether_address_map_entry",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_ENI_ETHER_ADDRESS_MAP_ENTRY",
                "key": {
                    "switch_id": "$SWITCH_ID",
                    "address": "00:AA:AA:AA:AA:00"
                },
                "attributes": [
                    *("SAI_ENI_ETHER_ADDRESS_MAP_ENTRY_ATTR_ENI_ID", "$eni_id")
                ]
            })
            create_eni_ether_address_map_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_inbound_routing_entry',
        ) as create_inbound_routing_entry_mock:
            command_processor.process_command({
                "name": "inbound_routing_entry",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_INBOUND_ROUTING_ENTRY",
                "key": {
                    "switch_id": "$SWITCH_ID",
                    "vni": "1000"
                },
                "attributes": [
                    *("SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION",
                      "SAI_INBOUND_ROUTING_ENTRY_ACTION_VXLAN_DECAP_PA_VALIDATE")]
            })
            create_inbound_routing_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_pa_validation_entry',
        ) as create_pa_validation_entry_mock:
            command_processor.process_command({
                "name": "pa_validation_entry",
                "op": "create",
                "type": "SAI_OBJECT_TYPE_PA_VALIDATION_ENTRY",
                "key": {
                    "switch_id": "$SWITCH_ID",
                    "eni_id": "$eni_id",
                    "sip": "10.10.2.20",
                    "vni": "1000"
                },
                "attributes": ["SAI_PA_VALIDATION_ENTRY_ATTR_ACTION", "SAI_PA_VALIDATION_ENTRY_ACTION_PERMIT"]
            })
            create_pa_validation_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_pa_validation_entry',
        ) as remove_pa_validation_entry_mock:
            command_processor.process_command(
                {
                    "name": "pa_validation_entry",
                    "op": "remove"
                })
            remove_pa_validation_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_inbound_routing_entry',
        ) as remove_inbound_routing_entry_mock:
            command_processor.process_command({
                "name": "inbound_routing_entry",
                "op": "remove",
            })
            remove_inbound_routing_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_remove_eni_ether_address_map_entry',
        ) as remove_eni_ether_address_map_entry_mock:
            command_processor.process_command({
                "name": "eni_ether_address_map_entry",
                "op": "remove",
            })
            remove_eni_ether_address_map_entry_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_eni',
                ) as remove_eni_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.ENI.value
                ):
            command_processor.process_command({
                "name": "eni_id",
                "op": "remove",
            })
            remove_eni_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_vnet',
                ) as remove_vnet_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.VNET.value
                ):
            command_processor.process_command({
                "name": "vnet_1",
                "op": "remove",
            })
            remove_vnet_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_dash_acl_group',
                ) as remove_dash_acl_group_out_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.DASH_ACL_GROUP.value
                ):
            command_processor.process_command({
                "name": "acl_out_1",
                "op": "remove",
            })
            remove_dash_acl_group_out_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_dash_acl_group',
                ) as remove_dash_acl_group_in_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.DASH_ACL_GROUP.value
                ):
            command_processor.process_command({
                "name": "acl_in_1",
                "op": "remove",
            })
            remove_dash_acl_group_in_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_direction_lookup_entry',
        ) as remove_direction_lookup_entry_mock:
            command_processor.process_command({
                "name": "direction_lookup_entry",
                "op": "remove",
            })
            remove_direction_lookup_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_vip_entry',
        ) as remove_vip_entry_mock:
            command_processor.process_command({
                "name": "vip_entry",
                "op": "remove",
            })
            remove_vip_entry_mock.assert_called_once()


# TODO create same test for SaiRedisClient
def test_command_create_remove_sai_objects_via_thrift():
    with patch.object(SaiThriftClient, 'start_thrift_client', return_value=(Mock(), Mock())):
        sai_client = SaiThriftClient(Mock())
        switch_oid = 9288674231451648

        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_vip_entry',
        ) as create_vip_entry_mock:
            vip_entry = SaiObject.VIP_ENTRY(sai_client, key={
                "switch_id": switch_oid,
                "vip": "192.168.0.1"
            })
            create_vip_entry_mock.assert_called_once()
            assert vip_entry.key == {
                "switch_id": switch_oid,
                "vip": "192.168.0.1"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_direction_lookup_entry',
        ) as create_direction_lookup_entry:
            direction_lookup_entry = SaiObject.DIRECTION_LOOKUP_ENTRY(
                sai_client,
                key={
                    "switch_id": switch_oid,
                    "vni": "2000"
                },
                attrs=[
                    *("SAI_DIRECTION_LOOKUP_ENTRY_ATTR_ACTION",
                      "SAI_DIRECTION_LOOKUP_ENTRY_ACTION_SET_OUTBOUND_DIRECTION"),
                ]
            )
            create_direction_lookup_entry.assert_called_once()
            assert direction_lookup_entry.key == {
                "switch_id": switch_oid,
                "vni": "2000"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_dash_acl_group',
                return_value=29554872554618881
        ) as create_acl_group_mock_in:
            acl_group_in = SaiObject.DASH_ACL_GROUP(
                sai_client,
                attrs=[
                    *("SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4"),
                ]
            )
            create_acl_group_mock_in.assert_called_once()
            assert acl_group_in.oid == 29554872554618881
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_dash_acl_group',
                return_value=29554872554618880
        ) as create_acl_group_mock_out:
            acl_group_out = SaiObject.DASH_ACL_GROUP(
                sai_client,
                attrs=[
                    *("SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4"),
                ]
            )
            create_acl_group_mock_out.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_vnet',
                return_value=32088147345014784
        ) as create_vnet:
            vnet = SaiObject.VNET(
                sai_client,
                attrs=[
                    *("SAI_VNET_ATTR_VNI", "2000"),
                ]
            )
            create_vnet.assert_called_once()
            assert vnet.oid == 32088147345014784
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_eni',
                return_value=30680772461461504
        ) as create_eni_mock:
            eni = SaiObject.ENI(sai_client, attrs=[
                *("SAI_ENI_ATTR_CPS", "10000"),
                *("SAI_ENI_ATTR_PPS", "100000"),
                *("SAI_ENI_ATTR_FLOWS", "100000"),
                *("SAI_ENI_ATTR_ADMIN_STATE", "True"),
                *("SAI_ENI_ATTR_VM_UNDERLAY_DIP", "10.10.2.10"),
                *("SAI_ENI_ATTR_VM_VNI", "9"),
                *("SAI_ENI_ATTR_VNET_ID", vnet.oid),
                *("SAI_ENI_ATTR_INBOUND_V4_STAGE1_DASH_ACL_GROUP_ID", acl_group_in.oid),
                *("SAI_ENI_ATTR_INBOUND_V4_STAGE2_DASH_ACL_GROUP_ID", acl_group_in.oid),
                *("SAI_ENI_ATTR_INBOUND_V4_STAGE3_DASH_ACL_GROUP_ID", acl_group_in.oid),
                *("SAI_ENI_ATTR_INBOUND_V4_STAGE4_DASH_ACL_GROUP_ID", acl_group_in.oid),
                *("SAI_ENI_ATTR_INBOUND_V4_STAGE5_DASH_ACL_GROUP_ID", acl_group_in.oid),
                *("SAI_ENI_ATTR_INBOUND_V6_STAGE1_DASH_ACL_GROUP_ID", acl_group_out.oid),
                *("SAI_ENI_ATTR_INBOUND_V6_STAGE2_DASH_ACL_GROUP_ID", acl_group_out.oid),
                *("SAI_ENI_ATTR_INBOUND_V6_STAGE3_DASH_ACL_GROUP_ID", acl_group_out.oid),
                *("SAI_ENI_ATTR_INBOUND_V6_STAGE4_DASH_ACL_GROUP_ID", acl_group_out.oid),
                *("SAI_ENI_ATTR_INBOUND_V6_STAGE5_DASH_ACL_GROUP_ID", acl_group_out.oid),
                *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE1_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE2_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE3_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE4_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE5_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE1_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE2_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE3_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE4_DASH_ACL_GROUP_ID", "0"),
                *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE5_DASH_ACL_GROUP_ID", "0"),
            ])
            create_eni_mock.assert_called_once()
            assert eni.oid == 30680772461461504
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_eni_ether_address_map_entry',
        ) as create_eni_ether_address_map_entry_mock:
            eni_ether_address_map_entry = SaiObject.ENI_ETHER_ADDRESS_MAP_ENTRY(
                sai_client,
                key={
                    "switch_id": switch_oid,
                    "address": "00:AA:AA:AA:AA:00"
                },
                attrs=[
                    *("SAI_ENI_ETHER_ADDRESS_MAP_ENTRY_ATTR_ENI_ID", eni.oid),
                ]
            )
            create_eni_ether_address_map_entry_mock.assert_called_once()
            assert eni_ether_address_map_entry.key == {
                "switch_id": switch_oid,
                "address": "00:AA:AA:AA:AA:00"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_inbound_routing_entry',
        ) as create_inbound_routing_entry_mock:
            inbound_routing_entry = SaiObject.INBOUND_ROUTING_ENTRY(
                sai_client,
                key={
                    "switch_id": switch_oid,
                    "vni": "1000"
                },
                attrs=[
                    *("SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION",
                      "SAI_INBOUND_ROUTING_ENTRY_ACTION_VXLAN_DECAP_PA_VALIDATE")]
            )
            create_inbound_routing_entry_mock.assert_called_once()
            assert inbound_routing_entry.key == {
                "switch_id": switch_oid,
                "vni": "1000"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_pa_validation_entry',
        ) as create_pa_validation_entry_mock:
            pa_validation_entry = SaiObject.PA_VALIDATION_ENTRY(
                sai_client,
                key={
                    "switch_id": switch_oid,
                    "eni_id": eni.oid,
                    "sip": "10.10.2.20",
                    "vni": "1000"
                },
                attrs=[*("SAI_PA_VALIDATION_ENTRY_ATTR_ACTION",
                         "SAI_PA_VALIDATION_ENTRY_ACTION_PERMIT")]
            )
            create_pa_validation_entry_mock.assert_called_once()
            assert pa_validation_entry.key == {
                "switch_id": switch_oid,
                "eni_id": eni.oid,
                "sip": "10.10.2.20",
                "vni": "1000"
            }

        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_pa_validation_entry',
        ) as remove_pa_validation_entry_mock:
            pa_validation_entry.remove()
            remove_pa_validation_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_inbound_routing_entry',
        ) as remove_inbound_routing_entry_mock:
            inbound_routing_entry.remove()
            remove_inbound_routing_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_remove_eni_ether_address_map_entry',
        ) as remove_eni_ether_address_map_entry_mock:
            eni_ether_address_map_entry.remove()
            remove_eni_ether_address_map_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_eni',
        ) as remove_eni_mock:
            eni.remove()
            remove_eni_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_vnet',
        ) as remove_vnet_mock:
            vnet.remove()
            remove_vnet_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_dash_acl_group',
        ) as remove_dash_acl_group_in_mock:
            acl_group_in.remove()
            remove_dash_acl_group_in_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_dash_acl_group',
        ) as remove_dash_acl_group_out_mock:
            acl_group_out.remove()
            remove_dash_acl_group_out_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_direction_lookup_entry',
        ) as remove_direction_lookup_entry_mock:
            direction_lookup_entry.remove()
            remove_direction_lookup_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_vip_entry',
        ) as remove_vip_entry_mock:
            vip_entry.remove()
            remove_vip_entry_mock.assert_called_once()


# TODO create same test for SaiRedisClient
def test_command_create_remove_sai_objects_via_thrift_directly():
    with patch.object(SaiThriftClient, 'start_thrift_client', return_value=(Mock(), Mock())):
        sai_client = SaiThriftClient(Mock())
        switch_oid = 9288674231451648

        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_vip_entry',
        ) as create_vip_entry_mock:
            vip_entry_key = sai_client.create(
                SaiObject.Type.VIP_ENTRY,
                key={
                    "switch_id": switch_oid,
                    "vip": "192.168.0.1"
                }
            )
            create_vip_entry_mock.assert_called_once()
            assert vip_entry_key == {
                "switch_id": switch_oid,
                "vip": "192.168.0.1"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_direction_lookup_entry',
        ) as create_direction_lookup_entry:
            direction_lookup_entry_key = sai_client.create(
                SaiObject.Type.DIRECTION_LOOKUP_ENTRY,
                key={
                    "switch_id": switch_oid,
                    "vni": "2000"
                },
                attrs=[
                    *("SAI_DIRECTION_LOOKUP_ENTRY_ATTR_ACTION",
                      "SAI_DIRECTION_LOOKUP_ENTRY_ACTION_SET_OUTBOUND_DIRECTION"),
                ]
            )
            create_direction_lookup_entry.assert_called_once()
            assert direction_lookup_entry_key == {
                "switch_id": switch_oid,
                "vni": "2000"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_dash_acl_group',
                return_value=29554872554618881
        ) as create_acl_group_mock_in:
            acl_group_in_oid = sai_client.create(
                SaiObject.Type.DASH_ACL_GROUP,
                attrs=[
                    *("SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4"),
                ]
            )
            create_acl_group_mock_in.assert_called_once()
            assert acl_group_in_oid == 29554872554618881
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_dash_acl_group',
                return_value=29554872554618880
        ) as create_acl_group_mock_out:
            acl_group_out_oid = sai_client.create(
                SaiObject.Type.DASH_ACL_GROUP,
                attrs=[
                    *("SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4"),
                ]
            )
            create_acl_group_mock_out.assert_called_once()
            assert acl_group_out_oid == 29554872554618880
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_vnet',
                return_value=32088147345014784
        ) as create_vnet:
            vnet_oid = sai_client.create(
                SaiObject.Type.VNET,
                attrs=[
                    *("SAI_VNET_ATTR_VNI", "2000"),
                ]
            )
            create_vnet.assert_called_once()
            assert vnet_oid == 32088147345014784
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_create_eni',
                return_value=30680772461461504
        ) as create_eni_mock:
            eni_oid = sai_client.create(
                SaiObject.Type.ENI,
                attrs=[
                    *("SAI_ENI_ATTR_CPS", "10000"),
                    *("SAI_ENI_ATTR_PPS", "100000"),
                    *("SAI_ENI_ATTR_FLOWS", "100000"),
                    *("SAI_ENI_ATTR_ADMIN_STATE", "True"),
                    *("SAI_ENI_ATTR_VM_UNDERLAY_DIP", "10.10.2.10"),
                    *("SAI_ENI_ATTR_VM_VNI", "9"),
                    *("SAI_ENI_ATTR_VNET_ID", vnet_oid),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE1_DASH_ACL_GROUP_ID", acl_group_in_oid),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE2_DASH_ACL_GROUP_ID", acl_group_in_oid),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE3_DASH_ACL_GROUP_ID", acl_group_in_oid),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE4_DASH_ACL_GROUP_ID", acl_group_in_oid),
                    *("SAI_ENI_ATTR_INBOUND_V4_STAGE5_DASH_ACL_GROUP_ID", acl_group_in_oid),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE1_DASH_ACL_GROUP_ID", acl_group_out_oid),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE2_DASH_ACL_GROUP_ID", acl_group_out_oid),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE3_DASH_ACL_GROUP_ID", acl_group_out_oid),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE4_DASH_ACL_GROUP_ID", acl_group_out_oid),
                    *("SAI_ENI_ATTR_INBOUND_V6_STAGE5_DASH_ACL_GROUP_ID", acl_group_out_oid),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE1_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE2_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE3_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE4_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V4_STAGE5_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE1_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE2_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE3_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE4_DASH_ACL_GROUP_ID", "0"),
                    *("SAI_ENI_ATTR_OUTBOUND_V6_STAGE5_DASH_ACL_GROUP_ID", "0"),
                ]
            )
            create_eni_mock.assert_called_once()
            assert eni_oid == 30680772461461504
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_eni_ether_address_map_entry',
        ) as create_eni_ether_address_map_entry_mock:
            eni_ether_address_map_entry_key = sai_client.create(
                SaiObject.Type.ENI_ETHER_ADDRESS_MAP_ENTRY,
                key={
                    "switch_id": switch_oid,
                    "address": "00:AA:AA:AA:AA:00"
                },
                attrs=[
                    *("SAI_ENI_ETHER_ADDRESS_MAP_ENTRY_ATTR_ENI_ID", eni_oid),
                ]
            )
            create_eni_ether_address_map_entry_mock.assert_called_once()
            assert eni_ether_address_map_entry_key == {
                "switch_id": switch_oid,
                "address": "00:AA:AA:AA:AA:00"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_inbound_routing_entry',
        ) as create_inbound_routing_entry_mock:
            inbound_routing_entry_key = sai_client.create(
                SaiObject.Type.INBOUND_ROUTING_ENTRY,
                key={
                    "switch_id": switch_oid,
                    "vni": "1000"
                },
                attrs=[
                    *("SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION",
                      "SAI_INBOUND_ROUTING_ENTRY_ACTION_VXLAN_DECAP_PA_VALIDATE")]
            )
            create_inbound_routing_entry_mock.assert_called_once()
            assert inbound_routing_entry_key == {
                "switch_id": switch_oid,
                "vni": "1000"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_create_pa_validation_entry',
        ) as create_pa_validation_entry_mock:
            pa_validation_entry_key = sai_client.create(
                SaiObject.Type.PA_VALIDATION_ENTRY,
                key={
                    "switch_id": switch_oid,
                    "eni_id": eni_oid,
                    "sip": "10.10.2.20",
                    "vni": "1000"
                },
                attrs=[
                    *("SAI_PA_VALIDATION_ENTRY_ATTR_ACTION", "SAI_PA_VALIDATION_ENTRY_ACTION_PERMIT")
                ]
            )
            create_pa_validation_entry_mock.assert_called_once()
            assert pa_validation_entry_key == {
                "switch_id": switch_oid,
                "eni_id": eni_oid,
                "sip": "10.10.2.20",
                "vni": "1000"
            }
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_pa_validation_entry',
        ) as remove_pa_validation_entry_mock:
            sai_client.remove(key=pa_validation_entry_key, obj_type=SaiObject.Type.PA_VALIDATION_ENTRY)
            remove_pa_validation_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_inbound_routing_entry',
        ) as remove_inbound_routing_entry_mock:
            sai_client.remove(key=inbound_routing_entry_key, obj_type=SaiObject.Type.INBOUND_ROUTING_ENTRY)
            remove_inbound_routing_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.'
                'sai_thrift_remove_eni_ether_address_map_entry',
        ) as remove_eni_ether_address_map_entry_mock:
            sai_client.remove(key=eni_ether_address_map_entry_key, obj_type=SaiObject.Type.ENI_ETHER_ADDRESS_MAP_ENTRY)
            remove_eni_ether_address_map_entry_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_eni',
                ) as remove_eni_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.ENI.value
                ):
            sai_client.remove(oid=eni_oid)
            remove_eni_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_vnet',
                ) as remove_vnet_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.VNET.value
                ):
            sai_client.remove(oid=vnet_oid)
            remove_vnet_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_dash_acl_group',
                ) as remove_dash_acl_group_in_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.DASH_ACL_GROUP.value
                ):
            sai_client.remove(oid=acl_group_in_oid)
            remove_dash_acl_group_in_mock.assert_called_once()
        with \
                patch(
                    'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_dash_acl_group',
                ) as remove_dash_acl_group_out_mock, \
                patch.object(
                    sai_client.thrift_client,
                    'sai_thrift_object_type_query',
                    return_value=SaiObject.Type.DASH_ACL_GROUP.value
                ):
            sai_client.remove(oid=acl_group_out_oid)
            remove_dash_acl_group_out_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_direction_lookup_entry',
        ) as remove_direction_lookup_entry_mock:
            sai_client.remove(key=direction_lookup_entry_key, obj_type=SaiObject.Type.DIRECTION_LOOKUP_ENTRY)
            remove_direction_lookup_entry_mock.assert_called_once()
        with patch(
                'sai_client.sai_thrift_client.sai_thrift_client.sai_adapter.sai_thrift_remove_vip_entry',
        ) as remove_vip_entry_mock:
            sai_client.remove(key=vip_entry_key, obj_type=SaiObject.Type.VIP_ENTRY)
            remove_vip_entry_mock.assert_called_once()

import re
from itertools import zip_longest
import ipaddress
import json
from sai_thrift import sai_headers
from sai_thrift.ttypes import *
from sai_thrift import ttypes
from sai_thrift.sai_headers import *
from saichallenger.common.sai_client.sai_thrift_client.sai_thrift_metadata import SaiMetadata
from saichallenger.common.sai_data import SaiObjType, SaiStatus


class ThriftConverter():
    def convert_attributes_to_thrift(attributes, obj_type):
        """
        [ "SAI_SWITCH_ATTR_PORT_LIST", "2:oid:0x0,oid:0x0" ] => { "port_list": sai_thrift_object_list_t(count=2, idlist=[0x0, 0x0]) }
        """
        for name, value in ThriftConverter.chunks(attributes, 2):
            yield ThriftConverter.convert_attribute_name_to_thrift(name), ThriftConverter.convert_value_to_thrift(value, name, obj_type)

    def convert_key_to_thrift(object_type, key = None):
        """
        Converts dictionary 'key' to the thrift key entry according to 'object_type':
        "vip_entry", { "switch_id": oid:0x0, "vip": "192.168.0.1" } => { "vip_entry": sai_thrift_vip_entry_t(switch_id = 0x0, vip = sai_ip_address_t("192.168.0.1"...)) }
        """
        if key is None:
            return {}

        key_t = getattr(ttypes, f'sai_thrift_{object_type}_t')
        if "vr" in key:
            key['vr_id'] = key['vr']
            del key['vr']
        if "dest" in key:
            key['destination'] = key['dest']
            del key['dest']
        return { object_type: key_t(**ThriftConverter.convert_key_values_to_thrift(object_type, key)) }

    def convert_attributes_from_thrift(attributes, obj_type):
        """
        TODO:
        [ ("SAI_SWITCH_ATTR_PORT_LIST", sai_thrift_object_list_t(...)), ("port_list", sai_thrift_object_list_t(...)) ] => [ "SAI_SWITCH_ATTR_PORT_LIST", "2:0x0,0x0" }
        """
        result_attrs = []
        for name, value in (attributes or {}).items():
            if not name.startswith('SAI'):
                continue
            result_attrs.append(name)
            result_attrs.append(ThriftConverter.convert_value_from_thrift(value, name, obj_type))

        return result_attrs


    # CONVERT TO THRIFT
    @staticmethod
    def convert_attribute_name_to_thrift(attr):
        """
        "SAI_SWITCH_ATTR_PORT_LIST" => "port_list"
        """
        return re.search('SAI_.*_ATTR_(.*)', attr).group(1).lower()

    @staticmethod
    def convert_value_to_thrift(value, attr_name, obj_type=None):
        """
        "100", "s32" => 100
        """
        if attr_name == None or attr_name == 'UTF8':
            value_type = ThriftConverter.get_value_type_by_thrift_spec(attr_name)
        else:
            value_type = ThriftConverter.get_attribute_type(attr_name)

        if value_type in [ 's8', 'u8', 's16', 'u16', 's32',
                           'u32', 's64', 'u64', 'ptr',
                           'encrypt_key', 'authkey',
                           'macsecsak', 'macsecauthkey', 'macsecsalt' ]:
            if isinstance(value, str):
                actual_value = getattr(sai_headers, value, None)
                if actual_value != None:
                    return actual_value
            return 0 if value == '' else int(value, 0)
        if value_type in [ 'booldata' ]:
            return value.lower() == "true" or value == "0"
        elif value_type in [ 'mac', 'ipv4', 'ipv6', 'chardata' ]:
            return str(value)
        elif value_type in [ 'oid' ]:
            return ThriftConverter.object_id(value)
        elif value_type in [ 'ipaddr' ]:
            return ThriftConverter.sai_ipaddress(value)
        elif value_type in [ 'ipprefix' ]:
            return ThriftConverter.sai_ipprefix(value)
        elif value_type in [ 'objlist' ]:
            return ThriftConverter.sai_object_list(value)
        elif value_type in [ 'u8list', 'u16list', 'u32list', 's8list', 's16list', 's32list' ]:
            return ThriftConverter.sai_int_list(value_type, value)
        elif value_type in [ 'u32range' , 's32range', 'u16range' ]:
            return ThriftConverter.sai_int_range(value_type, value)
        elif value_type in [ 'maplist' ]:
            return ThriftConverter.sai_map_list(value)
        elif value_type in [ 'aclcapability' ]:
            return ThriftConverter.sai_acl_capability(value)
        elif value_type in [ 'aclresource' ]:
            return ThriftConverter.sai_acl_resource(value)
        elif value_type in [ 'sysportconfiglist' ]:
            return ThriftConverter.sai_sysport_config_list(value)
        if value_type in [ 'aclaction' ]:
            return ThriftConverter.sai_acl_action(value, attr_name, obj_type)
        if value_type in [ 'aclfield' ]:
            return ThriftConverter.sai_acl_field(value, attr_name, obj_type)

        # TODO: add more string->thrift converters here
        raise NotImplementedError(f"{value_type}, {value}")

    @staticmethod
    def convert_key_values_to_thrift(object_type, key):
        """
        "vip_entry", { "switch_id": "oid:0x0", "vip": "192.186.0.1" } => { "switch_id": 0, "vip": sai_thrift_ip_address_t('192.168.0.1'...) }
        """
        key_spec = getattr(ttypes, f'sai_thrift_{object_type}_t').thrift_spec

        result = {}
        for spec_entry in key_spec[1:]:
            key_attr_name = spec_entry[2]
            key_attr_type = spec_entry[3]
            result[key_attr_name] = ThriftConverter.convert_value_to_thrift(key[key_attr_name], key_attr_type)
        return result

    @staticmethod
    def get_attribute_type(attr_name):
        """
        "SAI_SWITCH_ATTR_PORT_LIST" => "objlist"
        """
        if attr_name == 'SAI_FDB_FLUSH_ATTR_ENTRY_TYPE':
            return "s32"
        elif attr_name == 'SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID':
            return "oid"
        elif attr_name == 'SAI_FDB_FLUSH_ATTR_BV_ID':
            return "oid"
        return SaiMetadata[attr_name]

    @staticmethod
    def sai_object_list(object_list):
        """
        "2:oid:0x1,oid:0x2" => sai_thrift_object_list_t(count=2, idlist=[1,2])
        """
        splitted = object_list.split(':', 1)
        count = int(splitted[0])
        idlist = [ ThriftConverter.object_id(item) for item in splitted[1].split(',') ]
        return sai_thrift_object_list_t(count=count, idlist=idlist)

    @staticmethod
    def sai_int_list(value_type, value_data):
        """
        "4:1,2,3,4" => sai_thrift_{type}_list_t(count=4, {type}list=[1,2,3,4])
        """
        splitted = value_data.split(':', 1)
        count = int(splitted[0])
        thrift_list = [ ThriftConverter.get_enum_by_str(item) for item in splitted[1].split(',') ]
        sai_thrift_class = getattr(ttypes, 'sai_thrift_{}_list_t'.format(value_type[:-4]))
        return sai_thrift_class(count, thrift_list)

    @staticmethod
    def sai_int_range(value_type, range):
        """
        "1,7" => sai_thrift_{}_range_t(min=1, max=7)
        """
        splitted = range.split(',')
        sai_thrift_class = getattr(ttypes, 'sai_thrift_{}_range_t'.format(value_type[:-5]))
        return sai_thrift_class(min=splitted[0], max=splitted[1])

    @staticmethod
    def sai_map_list(value):
        """
        {"count":1,"list":[{"key":0,"value":0}]} =>  sai_thrift_map_list_t(count=1, maplist=[{"key":0,"value":0}])
        """
        val = json.loads(value)
        maplist = []
        for entry in val["list"]:
            maplist.append(sai_thrift_map_t(key=entry["key"], value=entry["value"]))
        return sai_thrift_map_list_t(maplist=maplist, count=val["count"])

    @staticmethod
    def sai_acl_capability(value):
        """
        false:1:0 => sai_thrift_acl_capability_t(is_action_list_mandatory="false",
            action_list=sai_thrift_s32_list_t(count=1, int32list=[0]))
        """
        splitted = value.split(':', 1)
        thrift_list = ThriftConverter.sai_int_list('s32list', splitted[1])
        return sai_thrift_acl_capability_t(is_action_list_mandatory=splitted[0], action_list=thrift_list)

    @staticmethod
    def sai_acl_resource(value):
        """
        {"count":1,"list":[{"avail_num":"","bind_point":"","stage":""}]} =>
            sai_thrift_acl_resource_t(count=1, [sai_thrift_acl_resource_t(stage=None, bind_point=None, avail_num=None)])
        """
        val = json.loads(value)
        resourcelist = []
        for r in val["list"]:
            avail_num = ThriftConverter.str2digit(r["avail_num"])
            bind_point = ThriftConverter.get_enum_by_str(r["bind_point"])
            stage = ThriftConverter.get_enum_by_str(r["stage"])
            resourcelist.append(sai_thrift_acl_resource_t(avail_num=avail_num, bind_point=bind_point, stage=stage))
        return sai_thrift_acl_resource_list_t(count=val["count"], resourcelist=resourcelist)

    @staticmethod
    def sai_acl_action(value, attr_name, obj_type):
        attribute_value = ""
        generic_type = ThriftConverter.get_generic_type(obj_type, attr_name)
        if generic_type == 's32':
            attribute_value = sai_thrift_attribute_value_t(aclfield=sai_thrift_acl_action_data_t(
                parameter=sai_thrift_acl_action_parameter_t(s32=ThriftConverter.get_enum_by_str(value))))
        elif generic_type == 'oid':
            attribute_value = sai_thrift_attribute_value_t(aclfield=sai_thrift_acl_action_data_t(
                parameter=sai_thrift_acl_action_parameter_t(oid=ThriftConverter.object_id(value))))
        else:
            raise NotImplementedError(f"{value} {attr_name}")

        if attribute_value is not None:
            attribute = sai_thrift_attribute_t(id=ThriftConverter.get_enum_by_str(attr_name), value=attribute_value)
            return attribute
        return None

    @staticmethod
    def sai_acl_field(value, attr_name, obj_type):
        attribute_value = ""
        generic_type = ThriftConverter.get_generic_type(obj_type, attr_name)
        if generic_type == 'ip4':
            # value 192.168.0.8&mask:255.255.255.255
            ipaddr = value.split("&")[0]
            mask = value.split(":")[1]
            attribute_value = sai_thrift_attribute_value_t(aclfield=sai_thrift_acl_field_data_t(data=sai_thrift_acl_field_data_data_t(ip4=ipaddr),
                                                                                                mask=sai_thrift_acl_field_data_mask_t(ip4=mask)))
        # u8, u16, u32
        elif generic_type[0] == 'u':
            # value 2048&mask:0xffff
            val = int(value.split("&")[0])
            mask = int(value.split(":")[1], 16)
            attribute_value = sai_thrift_attribute_value_t(aclfield=sai_thrift_acl_field_data_t(data=sai_thrift_acl_field_data_data_t(u32=val),
                                                                                                mask=sai_thrift_acl_field_data_mask_t(u32=mask)))
        else:
            raise NotImplementedError(f"{value} {attr_name}")

        if attribute_value is not None:
            attribute = sai_thrift_attribute_t(id=ThriftConverter.get_enum_by_str(attr_name), value=attribute_value)
            return attribute
        return None


    @staticmethod
    def str2digit(value):
        return int(value) if value.isdigit() else None

    @staticmethod
    def sai_sysport_config_list(value):
        """
        {"count":1,"list":[{"port_id":"","attached_switch_id":"","attached_core_index":"","attached_core_port_index":"","speed":"","num_voq":""}]} =>
            sai_thrift_system_port_config_list_t(count=1, [sai_thrift_system_port_config_t( port_id=None, ... )])
        """
        val = json.loads(value)
        configlist = []
        for r in val["list"]:
            configlist.append(sai_thrift_system_port_config_t(
                port_id=ThriftConverter.str2digit(r["port_id"]),
                attached_switch_id=ThriftConverter.str2digit(r["attached_switch_id"]),
                attached_core_index=ThriftConverter.str2digit(r["attached_core_index"]),
                attached_core_port_index=ThriftConverter.str2digit(r["attached_core_port_index"]),
                speed=ThriftConverter.str2digit(r["speed"]),
                num_voq=ThriftConverter.str2digit(r["num_voq"])))
        return sai_thrift_system_port_config_list_t(count=val["count"], configlist=configlist)

    @staticmethod
    def sai_ipaddress(addr_str):
        """
        "192.168.0.1" => sai_thrift_ip_address_t('192.168.0.1'...)
        """
        if '.' in addr_str:
            family = SAI_IP_ADDR_FAMILY_IPV4
            addr = sai_thrift_ip_addr_t(ip4=addr_str)
        elif ':' in addr_str:
            family = SAI_IP_ADDR_FAMILY_IPV6
            addr = sai_thrift_ip_addr_t(ip6=addr_str)
        else:
            return None

        return sai_thrift_ip_address_t(addr_family=family, addr=addr)

    @staticmethod
    def sai_ipprefix(prefix_str):
        """
        "192.168.1.0/24" => sai_thrift_ip_prefix_t(ip='192.168.1.0', mask='255.255.255.0')
        """
        if '/' not in prefix_str:
            print("Invalid IP prefix format")
            return None

        if '.' in prefix_str:
            family = SAI_IP_ADDR_FAMILY_IPV4
            ip = ipaddress.IPv4Network(prefix_str, strict=False)
            addr = sai_thrift_ip_addr_t(ip4=str(ip.network_address))
            mask = sai_thrift_ip_addr_t(ip4=str(ip.netmask))
        elif ':' in prefix_str:
            family = SAI_IP_ADDR_FAMILY_IPV6
            ip = ipaddress.IPv6Network(prefix_str, strict=False)
            addr = sai_thrift_ip_addr_t(ip6=ip.network_address.exploded)
            mask = sai_thrift_ip_addr_t(ip6=ip.netmask.exploded)
        else:
            return None

        ip_prefix = sai_thrift_ip_prefix_t(
            addr_family=family, addr=addr, mask=mask)
        return ip_prefix

    @staticmethod
    def object_id(oid):
        """
        None       => 0
        16         => 16
        "16"       => 16
        "oid:0x10" => 16
        """
        if oid == None or oid == 'null':
            return 0
        if isinstance(oid, str) and oid.startswith('oid:0x'):
            return int(oid[4:], 16)

        # FIXME: The OID always must be in "oid:0x0" format.
        #        We need this temporary workaround to handle the issue
        #        described in get_value_type_by_thrift_spec()
        return int(oid)

    # CONVERT FROM THRIFT
    @staticmethod
    def get_value_type_by_thrift_spec(thrift_spec):
        """
        sai_thrfit_ip_address_t => "ipaddr"
        """
        # FIXME: Sometimes, thrift_spec returns "None" for both "oid" and "int"
        #        E.g., For SAI_OBJECT_TYPE_DIRECTION_LOOKUP_ENTRY, thrift_spec will be
        #        (1, 10, 'switch_id', None, None), (2, 8, 'vni', None, None)
        if thrift_spec == None:
            return "oid"

        attribute_value_spec = getattr(ttypes, f'sai_thrift_attribute_value_t').thrift_spec
        for spec in attribute_value_spec[1:]:
            if spec[3] == thrift_spec:
                return spec[2]

        assert True, "Should not get here"

    @staticmethod
    def convert_value_from_thrift(value, attr_name, obj_type=None):
        """
        sai_thrift_ip_address_t('192.168.0.1'...), "ipaddr" => "192.168.0.1"
        """
        value_type = ThriftConverter.get_attribute_type(attr_name)
        if value_type in [ 's8', 'u8', 's16', 'u16',
                           'u32', 's64', 'u64',
                           'ptr', 'mac', 'ipv4', 'ipv6',
                           'chardata' ]:
            return str(value)
        elif value_type in [ 's32' ]:
            actual_value = ThriftConverter.get_str_by_enum(obj_type, attr_name, value)
            if actual_value != None:
                return actual_value
            return str(value)
        elif value_type in [ 'booldata' ]:
            return str(value).lower()
        elif value_type in [ 'objlist' ]:
            return ThriftConverter.from_sai_object_list(value)
        elif value_type == "oid":
            return "oid:" + hex(value)
        elif value_type in [ 'u8list', 'u16list', 'u32list',
                             's8list', 's16list', 's32list' ]:
            return ThriftConverter.from_sai_int_list(value_type, value, attr_name, obj_type)
        elif value_type in [ 'u32range' , 's32range', 'u16range' ]:
            return f"{value.min},{value.max}"
        elif value_type in [ 'maplist' ]:
            raise NotImplementedError(f"{value_type}, {value}")
        elif value_type in [ 'aclcapability' ]:
            return ThriftConverter.from_sai_acl_capability(value_type, value, attr_name, obj_type)
        elif value_type in [ 'aclresource' ]:
            return ThriftConverter.from_sai_acl_resource(value_type, value, attr_name, obj_type)
        elif value_type in [ 'sysportconfiglist' ]:
            return ThriftConverter.from_sai_sysport_config_list(value_type, value, attr_name, obj_type)
        elif value_type in [ 'aclaction' ]:
            raise NotImplementedError(f"{value_type}, {value}")
        elif value_type in [ 'aclfield' ]:
            raise NotImplementedError(f"{value_type}, {value}")

        # TODO: Add more thrift->string convertes here
        raise NotImplementedError(f"{value_type}, {value}")

    @staticmethod
    def from_sai_object_list(object_list):
        """
        sai_thrift_object_list_t(count=2, idlist=[1,2]) => "2:oid:0x1,oid:0x2"
        """
        if object_list.count == 0:
            return '0:null'
        result = f'{object_list.count}:'
        for ii in range(object_list.count):
            result += "oid:" + hex(object_list.idlist[ii])
            result += ","
        return result[:-1]

    @staticmethod
    def from_sai_int_list(value_type, object_list, attr_name=None, obj_type=None):
        """
        sai_thrift_{type}_list_t(count=2, {type}list=[1,2]) => "2:1,2"
        """
        prefix = "uint" if value_type.startswith("u") else "int"
        listvar = getattr(object_list, prefix + value_type[1:])
        result = f'{object_list.count}:'
        for ii in range(object_list.count):
            if value_type == 's32list' and attr_name is not None:
                actual_value = ThriftConverter.get_str_by_enum(obj_type, attr_name, listvar[ii])
                if actual_value != None:
                    listvar[ii] = actual_value
            result += str(listvar[ii])
            result += ","
        return result[:-1]

    @staticmethod
    def from_sai_acl_capability(value_type, object_list, attr_name, obj_type):
        """
        sai_thrift_s32_list_t(count=1, int32list=[0, 1] => "false:1:0"
        """
        is_action_list_mandatory = getattr(object_list, 'is_action_list_mandatory')
        action_list = getattr(object_list, 'action_list')
        listvar = ThriftConverter.from_sai_int_list('s32list', action_list, 'SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST', 'SAI_OBJECT_TYPE_ACL_TABLE')
        return f'{is_action_list_mandatory}'.lower() + ':' + listvar

    @staticmethod
    def from_sai_acl_resource(value_type, resource, attr_name, obj_type):
        """
        sai_thrift_acl_resource_t(count=1, [sai_thrift_acl_resource_t(stage=None, bind_point=None, avail_num=None)]) =>
          {"count":1,"list":[{"avail_num":"","bind_point":"","stage":""}]}
        """
        result = {
            "count": resource.count,
            "list": []
        }
        for r in resource.resourcelist:
            result["list"].append(
                {
                    "avail_num": str(r.avail_num),
                    "bind_point": ThriftConverter.get_str_by_enum('SAI_OBJECT_TYPE_ACL_TABLE', 'SAI_ACL_TABLE_GROUP_ATTR_ACL_BIND_POINT_TYPE_LIST', r.bind_point),
                    "stage": ThriftConverter.get_str_by_enum('SAI_OBJECT_TYPE_ACL_TABLE', 'SAI_ACL_TABLE_ATTR_ACL_STAGE', r.stage)
                }
            )
        return json.dumps(result).replace(" ", "")

    @staticmethod
    def from_sai_sysport_config_list(value_type, config, attr_name, obj_type):
        """
        sai_thrift_system_port_config_list_t(count=1, [sai_thrift_system_port_config_t( port_id=None, ... )]) =>
          {"count":1,"list":[{"port_id":"","attached_switch_id":"","attached_core_index":"","attached_core_port_index":"","speed":"","num_voq":""}]}
        """
        result = {
            "count": config.count,
            "list": []
        }
        for r in config.configlist:
            result["list"].append(
                {
                    "port_id": str(r.port_id),
                    "attached_switch_id": str(r.attached_switch_id),
                    "attached_core_index": str(r.attached_core_index),
                    "attached_core_port_index": str(r.attached_core_port_index),
                    "speed": str(r.speed),
                    "num_voq": str(r.num_voq)
                }
            )
        return json.dumps(result).replace(" ", "")

# AUXILARY

    @staticmethod
    def chunks(iterable, n, fillvalue=None):
        """
        Split iterable to chunks of length n
        [1, 2, 3, 4], 2 => [1, 2], [3, 4]
        """
        return zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue)

    @staticmethod
    def convert_to_sai_obj_type(obj_type):
        """
        SaiObjType.PORT        => SaiObjType.PORT
        "PORT"                 => SaiObjType.PORT
        "SAI_OBJECT_TYPE_PORT" => SaiObjType.PORT
        1                      => SaiObjType.PORT
        """
        if isinstance(obj_type, SaiObjType):
            return obj_type
        elif isinstance(obj_type, str):
            prefix = 'SAI_OBJECT_TYPE_'
            obj_type_without_prefix = obj_type
            if obj_type.startswith(prefix):
                obj_type_without_prefix = obj_type[len(prefix):]
            try:
                return getattr(SaiObjType, obj_type_without_prefix)
            except AttributeError:
                return None
        elif isinstance(obj_type, int):
            return SaiObjType(obj_type)
        return None

    @staticmethod
    def convert_to_sai_status_str(status):
        """
        15                        => "SAI_STATUS_NOT_IMPLEMENTED"
        "15"                      => "SAI_STATUS_NOT_IMPLEMENTED"
        SaiStatus.NOT_IMPLEMENTED => "SAI_STATUS_NOT_IMPLEMENTED"
        """
        name = None
        if isinstance(status, SaiStatus):
            name = status.name
        elif isinstance(status, str):
            name = SaiStatus(int(status)).name
        elif isinstance(status, int):
            name = SaiStatus(status).name
        return 'SAI_STATUS_' + name

    @staticmethod
    def get_sai_meta(obj_type, attr_name):
        """Get SAI meta data by SAI object type and attribute name"""
        try:
            with open("/etc/sai/sai.json", "r") as f:
                sai_json = json.loads(f.read())
        except IOError:
            return None

        if type(obj_type) == SaiObjType:
            obj_type = "SAI_OBJECT_TYPE_" + SaiObjType(obj_type).name
        else:
            assert type(obj_type) == str
            assert obj_type.startswith("SAI_OBJECT_TYPE_")

        for item in sai_json:
            if obj_type not in item.values(): continue
            attrs = item.get('attributes')
            for attr in attrs:
                if attr_name == attr.get('name'):
                    return attr
        return None

    @staticmethod
    def get_str_by_enum(obj_type, attr_name, enum_value):
        """Get enum member str name by enum member value"""
        meta = ThriftConverter.get_sai_meta(obj_type, attr_name)
        if meta is None:
            return None
        if meta['properties'].get('values') == None:
            return str(enum_value)
        for k, v in meta['properties']['values'].items():
            if v == enum_value:
                return k

        return None

    @staticmethod
    def get_enum_by_str(value):
        """Get enum member value by enum member name"""
        if isinstance(value, str) and value.startswith('SAI_'):
            return getattr(sai_headers, value, None)
        return int(value) if value.isdigit() else None

    @staticmethod
    def get_generic_type(obj_type, attr_name):
        """Get attribute generic type"""
        meta = ThriftConverter.get_sai_meta(obj_type, attr_name)
        if meta is None:
            return None
        return ThriftConverter.get_generic_short(meta['properties'].get('genericType'))
        #return meta['properties'].get('genericType')

    @staticmethod
    def get_generic_short(value):
        generic_types = {
            "bool"              : "bool",
            "sai_uint8_t"       : "u8",
            "sai_int8_t"        : "s8",
            "sai_uint16_t"      : "u16",
            "sai_int16_t"       : "s16",
            "sai_uint32_t"      : "u32",
            "sai_int32_t"       : "s32",
            "sai_uint64_t"      : "u64",
            "sai_mac_t"         : "mac",
            "sai_ipv4_t"        : "ip4",
            "sai_ipv6_t"        : "ip6",
            "sai_object_id_t"   : "oid",
            "sai_object_list_t" : "objlist",
            "sai_u8_list_t"     : "u8list"
        }
        return generic_types.get(value)

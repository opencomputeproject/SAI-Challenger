import re
from itertools import zip_longest
from sai_thrift import sai_headers
from sai_thrift.ttypes import *
from sai_thrift import ttypes
from sai_thrift.sai_headers import *
from saichallenger.common.sai_client.sai_thrift_client.sai_thrift_metadata import SaiMetadata
from saichallenger.common.sai_data import SaiObjType, SaiStatus


class ThriftConverter():
    def convert_attributes_to_thrift(attributes):
        """
        [ "SAI_SWITCH_ATTR_PORT_LIST", "2:0x0,0x0" ] => { "port_list": sai_thrift_object_list_t(count=2, idlist=[0x0, 0x0]) }
        """
        for name, value in ThriftConverter.chunks(attributes, 2):
            yield ThriftConverter.convert_attribute_name_to_thrift(name), ThriftConverter.convert_value_to_thrift(value, ThriftConverter.get_attribute_type(name))

    def convert_key_to_thrift(object_type, key = None):
        """
        Converts dictionary 'key' to the thrift key entry according to 'object_type':
        "vip_entry", { "switch_id": 0x0, "vip": "192.168.0.1" } => { "vip_entry": sai_thrift_vip_entry_t(switch_id = 0x0, vip = sai_ip_address_t("192.168.0.1"...)) }
        """
        if key is None:
            return {}

        key_t = getattr(ttypes, f'sai_thrift_{object_type}_t')
        return { object_type: key_t(**ThriftConverter.convert_key_values_to_thrift(object_type, key)) }

    def convert_attributes_from_thrift(attributes):
        """
        TODO:
        [ ("SAI_SWITCH_ATTR_PORT_LIST", sai_thrift_object_list_t(...)), ("port_list", sai_thrift_object_list_t(...)) ] => [ "SAI_SWITCH_ATTR_PORT_LIST", "2:0x0,0x0" }
        """
        result_attrs = []
        for name, value in (attributes or {}).items():
            if not name.startswith('SAI'):
                continue
            result_attrs.append(name)
            result_attrs.append(ThriftConverter.convert_value_from_thrift(value, ThriftConverter.get_attribute_type(name)))

        return result_attrs


    # CONVERT TO THRIFT
    @staticmethod
    def convert_attribute_name_to_thrift(attr):
        """
        "SAI_SWITCH_ATTR_PORT_LIST" => "port_list"
        """
        return re.search('SAI_.*_ATTR_(.*)', attr).group(1).lower()

    @staticmethod
    def convert_value_to_thrift(value, value_type):
        """
        "100", "s32" => 100
        """
        if value_type in [ 's8', 'u8', 's16', 'u16', 's32',
                           'u32', 's64', 'u64', 'ptr',
                           'encrypt_key', 'authkey',
                           'macsecsak', 'macsecauthkey', 'macsecsalt' ]:
            if isinstance(value, str):
                actual_value = getattr(sai_headers, value, None)
                if actual_value != None:
                    return actual_value
            return int(value)
        if value_type in [ 'booldata' ]:
            return value.lower() == "true" or value == "0"
        if value_type in [ 'mac', 'ipv4', 'ipv6', 'chardata' ]:
            return str(value)
        if value_type in [ 'oid' ]:
            return ThriftConverter.object_id(value)
        if value_type in [ 'ipaddr' ]:
            return ThriftConverter.sai_ipaddress(value)
        if value_type in [ 'ipprefix' ]:
            return ThriftConverter.sai_ipprefix(value)
        if value_type in [ 'objlist' ]:
            return ThriftConverter.sai_object_list(value)

        # TODO: add more string->thrift converters here

        raise NotImplementedError

    @staticmethod
    def convert_key_values_to_thrift(object_type, key):
        """
        "vip_entry", { "switch_id": "0x0", "vip": "192.186.0.1" } => { "switch_id": 0, "vip": sai_thrift_ip_address_t('192.168.0.1'...) }
        """
        key_spec = getattr(ttypes, f'sai_thrift_{object_type}_t').thrift_spec

        result = {}
        for spec_entry in key_spec[1:]:
            key_attr_name = spec_entry[2]
            key_attr_type = spec_entry[3]
            result[key_attr_name] = ThriftConverter.convert_value_to_thrift(key[key_attr_name], ThriftConverter.get_value_type_by_thrift_spec(key_attr_type))
        return result

    @staticmethod
    def get_attribute_type(attr_name):
        """
        "SAI_SWITCH_ATTR_PORT_LIST" => "objlist"
        """
        return SaiMetadata[attr_name]

    @staticmethod
    def sai_object_list(object_list):
        """
        "2:0x1,0x2" => sai_thrift_object_list_t(count=2, idlist=[1,2])
        """
        splitted = object_list.split(':')
        count = int(splitted[0])
        idlist = [ ThriftConverter.object_id(item) for item in splitted[1].split(',') ]
        return sai_thrift_object_list_t(count=count,
                                        idlist=idlist)

    @staticmethod
    def sai_ipaddress(addr_str):
        """
        "192.168.0.1" => sai_thrift_ip_address_t('192.168.0.1'...)
        """

        if '.' in addr_str:
            family = SAI_IP_ADDR_FAMILY_IPV4
            addr = sai_thrift_ip_addr_t(ip4=addr_str)
        if ':' in addr_str:
            family = SAI_IP_ADDR_FAMILY_IPV6
            addr = sai_thrift_ip_addr_t(ip6=addr_str)
        ip_addr = sai_thrift_ip_address_t(addr_family=family, addr=addr)

        return ip_addr

    @staticmethod
    def sai_ipprefix(prefix_str):
        """
        "192.168.1.0/24" => sai_thrift_ip_prefix_t(ip='192.168.1.0', mask='255.255.255.0')
        """
        addr_mask = prefix_str.split('/')
        if len(addr_mask) != 2:
            print("Invalid IP prefix format")
            return None

        if '.' in prefix_str:
            family = SAI_IP_ADDR_FAMILY_IPV4
            addr = sai_thrift_ip_addr_t(ip4=addr_mask[0])
            mask = ThriftConverter.num_to_dotted_quad(addr_mask[1])
            mask = sai_thrift_ip_addr_t(ip4=mask)
        if ':' in prefix_str:
            family = SAI_IP_ADDR_FAMILY_IPV6
            addr = sai_thrift_ip_addr_t(ip6=addr_mask[0])
            mask = ThriftConverter.num_to_dotted_quad(int(addr_mask[1]), ipv4=False)
            mask = sai_thrift_ip_addr_t(ip6=mask)

        ip_prefix = sai_thrift_ip_prefix_t(
            addr_family=family, addr=addr, mask=mask)
        return ip_prefix

    @staticmethod
    def object_id(oid):
        """
        None   => 0
        10     => 10
        "0x10" => 16
        """
        if oid == None:
            return 0
        if isinstance(oid, str) and oid.startswith('0x'):
            return int(oid, 16)
        return int(oid)

    # CONVERT FROM THRIFT

    @staticmethod
    def get_value_type_by_thrift_spec(thrift_spec):
        """
        sai_thrfit_ip_address_t => "ipaddr"
        """
        if thrift_spec == None:
            return "oid"

        attribute_value_spec = getattr(ttypes, f'sai_thrift_attribute_value_t').thrift_spec
        for spec in attribute_value_spec[1:]:
            if spec[3] == thrift_spec:
                return spec[2]

        assert True, "Should not get here"

    @staticmethod
    def convert_value_from_thrift(value, value_type):
        """
        sai_thrift_ip_address_t('192.168.0.1'...), "ipaddr" => "192.168.0.1"
        """
        if value_type in [ 'objlist' ]:
            return ThriftConverter.from_sai_object_list(value)

        # TODO: Add more thrift->string convertes here

        return str(value)

    @staticmethod
    def from_sai_object_list(object_list):
        """
        sai_thrift_object_list_t(count=2, idlist=[1,2]) => "2:0x1,0x2"
        """
        result = f'{object_list.count}:'
        for ii in range(object_list.count):
            result += str(hex(object_list.idlist[ii]))
            result += ","
        return result[:-1]

# AUXILARY

    @staticmethod
    def chunks(iterable, n, fillvalue=None):
        """
        Split iterable to chunks of length n
        [1, 2, 3, 4], 2 => [1, 2], [3, 4]
        """
        return zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue)

    @staticmethod
    def num_to_dotted_quad(address, ipv4=True):
        """
        Helper function to convert the ip address

        Args:
            address (str): IP address
            ipv4 (bool): determines what IP version is handled

        Returns:
            str: formatted IP address
        """
        import socket
        if ipv4 is True:
            mask = (1 << 32) - (1 << 32 >> int(address))
            return socket.inet_ntop(socket.AF_INET, struct.pack('>L', mask))

        mask = (1 << 128) - (1 << 128 >> int(address))
        i = 0
        result = ''
        for sign in str(hex(mask)[2:]):
            if (i + 1) % 4 == 0:
                result = result + sign + ':'
            else:
                result = result + sign
            i += 1
        return result[:-1]

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

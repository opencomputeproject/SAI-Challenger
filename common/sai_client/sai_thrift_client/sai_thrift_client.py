import json
import logging
from functools import wraps
from inspect import Signature
from ipaddress import IPv6Interface, IPv4Interface, AddressValueError
from itertools import zip_longest
from sai import SaiObjType
from sai_client.sai_client import SaiClient
from sai_client.sai_thrift_client.sai_thrift_status import SaiStatus
from sai_data import SaiData
from sai_object import SaiObject
from sai_thrift import sai_rpc, sai_adapter, ttypes, sai_headers
from sai_thrift.sai_headers import SAI_IP_ADDR_FAMILY_IPV6, SAI_IP_ADDR_FAMILY_IPV4
# noinspection PyPep8Naming
from sai_thrift.ttypes import (
    sai_thrift_exception as SaiThriftException,
    sai_thrift_ip_addr_t,
    sai_thrift_ip_address_t,
    sai_thrift_ip_prefix_t
)
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket, TTransport
from typing import Iterable, Mapping, Union


# TODO Add SAI to environment and use sai_utils.sai_ipaddress
def sai_ipaddress(addr_str):
    """
    Set SAI IP address, assign appropriate type and return
    sai_thrift_ip_address_t object

    Args:
        addr_str (str): IP address string

    Returns:
        sai_thrift_ip_address_t: object containing IP address family and number
    """

    if '.' in addr_str:
        family = SAI_IP_ADDR_FAMILY_IPV4
        addr = sai_thrift_ip_addr_t(ip4=addr_str)
    if ':' in addr_str:
        family = SAI_IP_ADDR_FAMILY_IPV6
        addr = sai_thrift_ip_addr_t(ip6=addr_str)
    ip_addr = sai_thrift_ip_address_t(addr_family=family, addr=addr)

    return ip_addr


def sai_ip_interface(addr_str):
    try:
        iface = IPv4Interface(addr_str)
    except AddressValueError:
        try:
            iface = IPv6Interface(addr_str)
        except Exception:
            raise
        else:
            addr_family = sai_headers.SAI_IP_ADDR_FAMILY_IPV6
    else:
        addr_family = sai_headers.SAI_IP_ADDR_FAMILY_IPV4

    return sai_thrift_ip_prefix_t(
        addr_family=addr_family,
        addr=sai_ipaddress(str(iface.ip)),
        mask=sai_ipaddress(str(iface.netmask))
    )


def chunks(iterable, n, fillvalue=None):
    """Split iterable to chunks of length n"""
    return zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue)


class SaiThriftExceptionGroup(Exception):
    def __init__(self, msg, exceptions, *args, **kwargs):
        super().__init__(self, msg, *args, **kwargs)
        self.exceptions = exceptions


class ThriftValueError(ValueError):
    ...


def assert_status(method):
    @wraps(method)
    def method_wrapper(self, *args, do_assert=True, **kwargs):
        try:
            result = method(self, *args, **kwargs)
        except SaiThriftException as e:
            if do_assert:
                raise AssertionError from e
            else:
                return SaiStatus(e.status).name
        if do_assert and result is not None:
            return result
        else:
            return SaiStatus.SAI_STATUS_SUCCESS.name

    return method_wrapper


class SaiThriftClient(SaiClient):
    """Thrift SAI client implementation to wrap low level SAI calls"""

    def __init__(self, client_config):
        self.thrift_client, self.thrift_transport = self.start_thrift_client(client_config)

    @staticmethod
    def start_thrift_client(driver_config):
        transport = TSocket.TSocket(driver_config['ip'], driver_config['port'])
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        transport.open()
        return sai_rpc.Client(protocol), transport

    def __del__(self):
        self.thrift_transport.close()

    # region CRUD
    @assert_status
    def create(self, obj_type, *, key=None, attrs=()):
        oid_or_status = self._operate('create', attrs=attrs, obj_type=obj_type, key=key)
        return oid_or_status if key is None else key

    @assert_status
    def remove(self, *, oid=None, obj_type=None, key=None):
        return self._operate('remove', attrs=(), oid=oid, obj_type=obj_type, key=key)  # attrs are not needed on remove

    @assert_status
    def set(self, *, oid=None, obj_type=None, key=None, attr=()):
        return self._operate_attributes('set', attrs=attr, oid=oid, obj_type=obj_type, key=key)

    @assert_status
    def get(self, *, oid=None, obj_type=None, key=None, attrs=()):
        # TODO First design of this function seems to consume multiple attributes?
        raw_result = self._operate_attributes('get', attrs=attrs, oid=oid, obj_type=obj_type, key=key)

        try:
            result = json.dumps(raw_result[0])
        except IndexError:
            logging.exception(f'Unable unpack gee attrs result for oid: {oid}, key: {key}, obj_type {obj_type} '
                              f'attrs: {attrs} result data: {raw_result}')
            result = '[]'

        # TODO rework, because seems Redis specific
        return SaiData(result)

    # endregion CRUD

    def create_object(self, obj_type, key=None, attrs=()):
        return SaiObject(self, obj_type, key=key, attrs=attrs)

    @classmethod
    def _form_obj_key(cls, oid, obj_type_name, key, sai_thrift_function):
        sai_thrift_function_params = Signature.from_callable(sai_thrift_function).parameters
        if key is not None:
            obj_key_t = getattr(ttypes, f'sai_thrift_{obj_type_name}_t')
            if obj_type_name in sai_thrift_function_params.keys():
                # Check region Convert object key for realizations
                # TODO move to separate classes calls
                return {obj_type_name: obj_key_t(**cls._convert_obj_key(obj_type_name, key))}
            else:
                return {}
        elif oid is not None:
            # TODO Check sai-thrift for SWITCH. Seems like defect because oid must to be used
            param_name = f"{obj_type_name}_oid"
            if param_name in sai_thrift_function_params.keys():
                return {param_name: oid}
            else:
                return {}
        else:
            return {}

    @staticmethod
    def oid_to_int(oid):
        if isinstance(oid, int):
            return oid
        elif isinstance(oid, str) and oid.startswith('0x'):
            return int(oid, 16)
        else:
            return int(oid)

    def get_object_type(self, oid, default=None) -> SaiObjType:
        """
            Try to calculate object type from oid if default type is not provided
        """

        default_obj_type = SaiObject.normalize_obj_type(default)
        calculated_obj_type_exception = None
        if oid is not None and default_obj_type is None:
            try:
                calculated_oid_id = self.thrift_client.sai_thrift_object_type_query(self.oid_to_int(oid))
            except Exception as calculated_obj_type_exception:
                calculated_oid_id = self.oid_to_int(oid) >> 48
            if calculated_oid_id != 0:
                calculated_oid_obj_type = SaiObject.Type(calculated_oid_id)
            else:
                calculated_oid_obj_type = None
        else:
            calculated_oid_obj_type = None
        if default_obj_type is None and calculated_oid_obj_type is None:
            raise ValueError(
                f'Unable find appropriate Sai object type for oid: {oid}, default object type {default}'
            ) from calculated_obj_type_exception
        else:
            obj_type = default_obj_type or calculated_oid_obj_type
        return obj_type

    @staticmethod
    def _substitute_headers_attr_value(value):
        if isinstance(value, str):
            return getattr(sai_headers, value, value)
        else:
            return value

    @classmethod
    def _convert_attrs(cls, attrs: Union[Mapping, Iterable], obj_type_name: str):
        prefix = f'SAI_{obj_type_name.upper()}_ATTR_'
        for attr, value in attrs.items() if isinstance(attrs, Mapping) else chunks(attrs, 2):
            value = cls._substitute_headers_attr_value(value)
            if hasattr(sai_headers, attr) and attr.startswith(prefix):
                # Check region Convert object attr
                # TODO move to separate classes calls
                yield cls._convert_obj_attr(obj_type_name, attr[len(prefix):].lower(), value)
            else:
                raise ValueError(f'Attribute {attr} cannot be converted')

    def _operate(self, operation, attrs=(), oid=None, obj_type=None, key=None):
        if oid is not None and key is not None:
            raise ValueError('Both oid and key are specified')

        if oid is not None:
            oid = self.oid_to_int(oid)

        obj_type_name = self.get_object_type(oid, default=obj_type).name.lower()

        sai_thrift_function = getattr(sai_adapter, f'sai_thrift_{operation}_{obj_type_name}')

        obj_key = self._form_obj_key(oid, obj_type_name, key, sai_thrift_function)
        attr_kwargs = dict(self._convert_attrs(attrs, obj_type_name))

        return sai_thrift_function(self.thrift_client, **obj_key, **attr_kwargs)

    def _unwrap_attr_thrift_dict_to_sai_challendger_list(self, sai_value):
        def _():
            for key, value in (sai_value or {}).items():
                if not key.startswith('SAI'):
                    continue
                yield key, value

        return list(_())

    def _operate_attributes(self, operation, attrs=(), oid=None, obj_type=None, key=None):
        if oid is not None and key is not None:
            raise ValueError('Both oid and key are specified')
        obj_type_name = self.get_object_type(oid, default=obj_type).name.lower()

        # thrift functions operating one attribute a time
        exceptions = []
        result = []
        for attr, value in self._convert_attrs(attrs, obj_type_name):
            sai_thrift_function = getattr(sai_adapter, f'sai_thrift_{operation}_{obj_type_name}_attribute')
            try:
                obj_key = self._form_obj_key(oid, obj_type_name, key, sai_thrift_function)
                thrift_attr_value = sai_thrift_function(
                    self.thrift_client,
                    **obj_key,
                    **{attr: value}
                )
                result.extend(self._unwrap_attr_thrift_dict_to_sai_challendger_list(thrift_attr_value))
            except SaiThriftException as e:
                exceptions.append(e)
                result.append(e)
        if exceptions:
            first_exc, *other_excs = exceptions
            cause = None
            if other_excs:
                cause = SaiThriftExceptionGroup(f'Bulk operation failed: {other_excs}', other_excs)
            raise first_exc from cause
        else:
            return result

    def cleanup(self):
        # TODO define
        ...

    # region Convert object key
    """During CRUDing SAI objects by DSL values has to be converted to acceptable by Thrift"""

    @staticmethod
    def _convert_equivalence_obj_key(key):
        return key

    @classmethod
    def _convert_obj_key(cls, obj_type_name, key):
        return getattr(cls, f"_convert_{obj_type_name}_key", cls._convert_equivalence_obj_key)(key)

    @staticmethod
    def _convert_vlan_entry_key(key):
        def _():
            for item, value in key.items():
                if item == 'vip':
                    yield item, sai_ipaddress(value)
                else:
                    yield item, value

        return dict(_())

    @staticmethod
    def _convert_vip_entry_key(key):
        def _():
            for item, value in key.items():
                if item == 'vip':
                    yield item, sai_ipaddress(value)
                else:
                    yield item, value

        return dict(_())

    @staticmethod
    def _convert_direction_lookup_entry_key(key):
        def _():
            for item, value in key.items():
                if item == 'vni':
                    yield item, int(value)
                else:
                    yield item, value

        return dict(_())

    @staticmethod
    def _convert_pa_validation_entry_key(key):
        def _():
            for item, value in key.items():
                if item == 'vnet_id':
                    yield item, SaiThriftClient.oid_to_int(value)
                if item == 'vni':
                    yield item, int(value)
                elif item == 'sip':
                    yield item, sai_ipaddress(value)
                else:
                    yield item, value

        return dict(_())

    @staticmethod
    def _convert_inbound_routing_entry_key(key):
        def _():
            for item, value in key.items():
                if item in {'switch_id', 'eni_id'}:
                    yield item, SaiThriftClient.oid_to_int(value)
                elif item in {'sip', 'sip_mask'}:
                    yield item, sai_ipaddress(value)
                if item in {'vni', 'priority'}:
                    yield item, int(value)
                else:
                    yield item, value

        return dict(_())

    @staticmethod
    def _convert_outbound_routing_entry_key(key):
        def _():
            for item, value in key.items():
                if item == 'destination':
                    yield item, sai_ip_interface(value)
                else:
                    yield item, value

        return dict(_())

    @staticmethod
    def _convert_outbound_ca_to_pa_entry_key(key):
        def _():
            for item, value in key.items():
                if item == 'dip':
                    yield item, sai_ipaddress(value)
                else:
                    yield item, value

        return dict(_())

    # endregion Convert object key

    # region Convert object attr
    @staticmethod
    def _convert_equivalence_obj_attr(key, value):
        return key, value

    @classmethod
    def _convert_obj_attr(cls, obj_type_name, attr, value):
        return getattr(cls, f"_convert_{obj_type_name}_attr", cls._convert_equivalence_obj_attr)(attr, value)

    @staticmethod
    def _convert_eni_attr(attr, value):
        if attr in {"dip", 'vm_underlay_dip'}:
            return attr, sai_ipaddress(value)
        elif attr in {
            'cps',
            'pps',
            'flows',
            'vm_vni',
            "inbound_v4_stage1_dash_acl_group_id",
            "inbound_v4_stage2_dash_acl_group_id",
            "inbound_v4_stage3_dash_acl_group_id",
            "inbound_v4_stage4_dash_acl_group_id",
            "inbound_v4_stage5_dash_acl_group_id",
            "inbound_v6_stage1_dash_acl_group_id",
            "inbound_v6_stage2_dash_acl_group_id",
            "inbound_v6_stage3_dash_acl_group_id",
            "inbound_v6_stage4_dash_acl_group_id",
            "inbound_v6_stage5_dash_acl_group_id",
            "outbound_v4_stage1_dash_acl_group_id",
            "outbound_v4_stage2_dash_acl_group_id",
            "outbound_v4_stage3_dash_acl_group_id",
            "outbound_v4_stage4_dash_acl_group_id",
            "outbound_v4_stage5_dash_acl_group_id",
            "outbound_v6_stage1_dash_acl_group_id",
            "outbound_v6_stage2_dash_acl_group_id",
            "outbound_v6_stage3_dash_acl_group_id",
            "outbound_v6_stage4_dash_acl_group_id",
            "outbound_v6_stage5_dash_acl_group_id",
        }:
            return attr, int(value)
        elif attr == 'admin_state':
            return attr, str(value).lower() == 'true'
        else:
            return attr, value

    @staticmethod
    def _convert_vnet_attr(attr, value):
        if attr == "vni":
            return attr, int(value)
        else:
            return attr, value

    @staticmethod
    def _convert_outbound_ca_to_pa_entry_attr(attr, value):
        if attr == "underlay_dip":
            return attr, sai_ipaddress(value)
        elif attr == "use_dst_vnet_vni":
            return attr, str(value).lower() == 'true'
        else:
            return attr, value

    @staticmethod
    def _convert_acl_rule_attr(attr, value):
        if attr in {"dip", "sip"}:
            return attr, sai_ipaddress(value)
        elif attr in {
            "protocol"
            "src_port"
            "dst_port"
            "priority"
            "action"
        }:
            return attr, int(value)
        else:
            return attr, value

    # endregion Convert object attr

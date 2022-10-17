import json
import logging
from functools import wraps
from saichallenger.common.sai_client.sai_client import SaiClient
from saichallenger.common.sai_client.sai_thrift_client.sai_thrift_utils import *
from saichallenger.common.sai_data import SaiData
from saichallenger.common.sai_data import SaiObjType
from sai_thrift import sai_rpc, sai_adapter
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket, TTransport


def assert_status(method):
    @wraps(method)
    def method_wrapper(self, *args, do_assert=True, **kwargs):
        try:
            result = method(self, *args, **kwargs)
        except Exception as e:
            if do_assert:
                raise AssertionError from e
            else:
                # TODO: pick correct STATUS
                return sai_headers.SAI_STATUS_FAILURE
        if do_assert and result is not None:
            return result
        else:
            return sai_headers.SAI_STATUS_SUCCESS

    return method_wrapper


class SaiThriftClient(SaiClient):
    """Thrift SAI client implementation to wrap low level SAI calls"""

    def __init__(self, client_config):
        self.thrift_transport = TSocket.TSocket(client_config['ip'], client_config['port'])
        self.thrift_transport = TTransport.TBufferedTransport(self.thrift_transport)
        protocol = TBinaryProtocol.TBinaryProtocol(self.thrift_transport)
        self.thrift_transport.open()
        self.thrift_client = sai_rpc.Client(protocol)

    def __del__(self):
        self.thrift_transport.close()

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
            result = json.dumps(raw_result)
        except IndexError:
            logging.exception(f'Unable unpack gee attrs result for oid: {oid}, key: {key}, obj_type {obj_type} '
                              f'attrs: {attrs} result data: {raw_result}')
            result = '[]'

        return SaiData(result)

    def get_object_type(self, oid, default=None) -> SaiObjType:
        if default != None:
            return ThriftConverter.convert_to_sai_obj_type(default)

        if oid != None:
            try:
                return SaiObjType(self.thrift_client.sai_thrift_object_type_query(ThirftConverter.object_id(oid)))
            except Exception as e:
                raise Exception
        return SaiObjType(0)

    def _operate(self, operation, attrs=(), oid=None, obj_type=None, key=None):
        if oid is not None and key is not None:
            raise ValueError('Both oid and key are specified')

        if oid is not None:
            oid = ThriftConverter.object_id(oid)

        obj_type_name = self.get_object_type(oid, default=obj_type).name.lower()
        object_key = ThriftConverter.convert_key_to_thrift(obj_type_name, key)
        if oid is not None:
            object_key[f'{obj_type_name}_oid'] = oid
        sai_thrift_function = getattr(sai_adapter, f'sai_thrift_{operation}_{obj_type_name}')

        attr_kwargs = dict(ThriftConverter.convert_attributes_to_thrift(attrs))

        return sai_thrift_function(self.thrift_client, **object_key, **attr_kwargs)

    def _operate_attributes(self, operation, attrs=(), oid=None, obj_type=None, key=None):
        if oid is not None and key is not None:
            raise ValueError('Both oid and key are specified')

        if oid is not None:
            oid = ThriftConverter.object_id(oid)

        obj_type_name = self.get_object_type(oid, default=obj_type).name.lower()
        object_key = ThriftConverter.convert_key_to_thrift(obj_type_name, key)
        sai_thrift_function = getattr(sai_adapter, f'sai_thrift_{operation}_{obj_type_name}_attribute')

        result = []

        for attr, value in ThriftConverter.convert_attributes_to_thrift(attrs):
            thrift_attr_value = sai_thrift_function(self.thrift_client, **object_key, **{attr: value})
            result.extend(ThriftConverter.convert_attributes_from_thrift(thrift_attr_value))

        return result

    def cleanup(self):
        # TODO define
        ...


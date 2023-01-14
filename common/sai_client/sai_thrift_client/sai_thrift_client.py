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
    def method_wrapper(self, *args):
        do_assert = args[-1]
        try:
            result = method(self, *args)
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

    def __init__(self, cfg):
        self.config = cfg
        self.thrift_transport = TSocket.TSocket(cfg['ip'], cfg['port'])
        self.thrift_transport = TTransport.TBufferedTransport(self.thrift_transport)
        protocol = TBinaryProtocol.TBinaryProtocol(self.thrift_transport)
        self.thrift_transport.open()
        self.thrift_client = sai_rpc.Client(protocol)
        self.sai_type_map = {}
        self.rec2vid = {}

    def __del__(self):
        self.thrift_transport.close()

    @staticmethod
    def obj_to_items(obj):
        obj_type = None
        oid = None
        key = None
        if type(obj) == str and obj.startswith("oid:0x"):
            oid = obj
        elif type(obj) == str:
            obj = obj.split(":", 1)
            obj_type = obj[0]
            if len(obj) > 1:
                if obj[1].startswith("oid:0x"):
                    oid = obj[1]
                else:
                    if obj_type == "SAI_OBJECT_TYPE_FDB_ENTRY":
                        if "bvid" in obj[1]:
                            # FDB key was provided in Redis format..
                            obj[1] = obj[1].replace("bvid", "bv_id")
                            obj[1] = obj[1].replace("mac", "mac_address")
                    key = json.loads(obj[1])
        elif type(obj) == SaiObjType:
            obj_type = obj
        else:
            assert False, "Unsupported OID format type {}".format(type(obj))

        return obj_type, oid, key

    @assert_status
    def create(self, obj, attrs, do_assert=True):
        obj_type, _, key = self.obj_to_items(obj)
        oid_or_status = self._operate('create', attrs=attrs, obj_type=obj_type, key=key)
        if key is None and type(oid_or_status) == int:
            if type(obj_type) == str:
                obj_type = SaiObjType[obj_type.replace("SAI_OBJECT_TYPE_", "")]
            self.sai_type_map[oid_or_status] = obj_type
        return ("oid:" + hex(oid_or_status)) if key is None else key

    @assert_status
    def remove(self, obj, do_assert=True):
        obj_type, oid, key = self.obj_to_items(obj)
        return self._operate('remove', attrs=(), oid=oid, obj_type=obj_type, key=key)  # attrs are not needed on remove

    @assert_status
    def set(self, obj, attr, do_assert=True):
        obj_type, oid, key = self.obj_to_items(obj)
        return self._operate_attributes('set', attrs=attr, oid=oid, obj_type=obj_type, key=key)

    def get(self, obj, attrs, do_assert=True):
        obj_type, oid, key = self.obj_to_items(obj)
        raw_result = self._operate_attributes('get', attrs=attrs, oid=oid, obj_type=obj_type, key=key)
        if len(raw_result) == 0:
            if do_assert:
                assert False, f"get({obj}, {attrs}, True) operation failed!"
            if attrs[1].startswith("1:"):
                return "SAI_STATUS_BUFFER_OVERFLOW", SaiData('["", "128"]')
            return "SAI_STATUS_FAILURE", None
        try:
            result = json.dumps(raw_result)
        except IndexError:
            logging.exception(f'Unable unpack get attrs result for oid: {oid}, key: {key}, obj_type {obj_type} '
                              f'attrs: {attrs} result data: {raw_result}')
            result = '[]'

        if do_assert:
            return SaiData(result)
        return "SAI_STATUS_SUCCESS", SaiData(result)

    def get_object_type(self, oid, default=None) -> SaiObjType:
        if default != None:
            return ThriftConverter.convert_to_sai_obj_type(default)

        if oid != None:
            try:
                obj_type = self.sai_type_map.get(oid, None)
                if obj_type is None:
                    # FIXME: Looks like self.thrift_client.sai_thrift_object_type_query() is broken for BMv2.
                    obj_type = SaiObjType(self.thrift_client.sai_thrift_object_type_query(ThriftConverter.object_id(oid)))
                return obj_type
            except Exception as e:
                raise Exception
        return SaiObjType(0)

    def _operate(self, operation, attrs=(), oid=None, obj_type=None, key=None):
        if oid is not None and key is not None:
            raise ValueError('Both OID and key are specified')

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
            if obj_type_name != "switch":
                object_key = {obj_type_name + "_oid": oid}
            thrift_attr_value = sai_thrift_function(self.thrift_client, **object_key, **{attr: value})
            if operation == 'set':
                # No need to have a list here, since set always takes only one attribute at a time
                result = ThriftConverter.convert_to_sai_status_str(thrift_attr_value)
            else:
                result.extend(ThriftConverter.convert_attributes_from_thrift(thrift_attr_value))

        return result

    def cleanup(self):
        # TODO define
        ...


import json
import logging
import subprocess
import time
from functools import wraps
from saichallenger.common.sai_client.sai_client import SaiClient
from saichallenger.common.sai_client.sai_thrift_client.sai_thrift_utils import *
from saichallenger.common.sai_data import SaiData
from saichallenger.common.sai_data import SaiObjType
from sai_thrift import sai_rpc, sai_adapter
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket, TTransport


class SaiThriftClient(SaiClient):
    """Thrift SAI client implementation to wrap low level SAI calls"""

    def __init__(self, cfg):
        self.config = cfg.copy()
        self.thrift_transport = None
        self.thrift_client = None
        self.sai_type_map = {}
        self.rec2vid = {}
        # We need it here to make SAI CLI work for Thrift RPC
        self.thrift_transport = TSocket.TSocket(self.config['ip'], self.config['port'])
        self.thrift_transport = TTransport.TBufferedTransport(self.thrift_transport)
        protocol = TBinaryProtocol.TBinaryProtocol(self.thrift_transport)
        self.thrift_transport.open()
        self.thrift_client = sai_rpc.Client(protocol)

    def __del__(self):
        if self.thrift_transport:
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

    def create(self, obj, attrs, do_assert=True):
        obj_type, _, key = self.obj_to_items(obj)
        status, result = self._operate('create', attrs=attrs, obj_type=obj_type, key=key)
        if key is None and type(result) == int:
            if type(obj_type) == str:
                obj_type = SaiObjType[obj_type.replace("SAI_OBJECT_TYPE_", "")]
            self.sai_type_map[result] = obj_type

        vid = None
        if status == 'SAI_STATUS_SUCCESS':
            vid = ("oid:" + hex(result)) if key is None else key

        if do_assert:
            assert status == 'SAI_STATUS_SUCCESS', f"create({obj}, {attrs}) --> {status}"
            return vid
        return status, vid

    def remove(self, obj, do_assert=True):
        obj_type, oid, key = self.obj_to_items(obj)
        status, _ = self._operate('remove', attrs=(), oid=oid, obj_type=obj_type, key=key)  # attrs are not needed on remove
        if do_assert:
            assert status == 'SAI_STATUS_SUCCESS', f"remove({obj}) --> {status}"
        return status

    def set(self, obj, attr, do_assert=True):
        obj_type, oid, key = self.obj_to_items(obj)
        status, _ = self._operate_attributes('set', attrs=attr, oid=oid, obj_type=obj_type, key=key)
        if do_assert:
            assert status == 'SAI_STATUS_SUCCESS', f"set({obj}, {attr}) --> {status}"
        return status

    def get(self, obj, attrs, do_assert=True):
        obj_type, oid, key = self.obj_to_items(obj)
        status, raw_result = self._operate_attributes('get', attrs=attrs, oid=oid, obj_type=obj_type, key=key)
        if len(raw_result) == 0:
            if do_assert:
                assert False, f"get({obj}, {attrs}, True) operation failed!"
            if status != "SAI_STATUS_BUFFER_OVERFLOW":
                return status, None
            if attrs[1].startswith("1:"):
                return status, SaiData('["", "128"]')
            if attrs[0].startswith('SAI_SWITCH_ATTR_ACL_STAGE'):
                return status, SaiData('["", "false:512:0"]')
            if attrs[0].startswith("SAI_SWITCH_ATTR_AVAILABLE_ACL_"):
                return status, SaiData(json.dumps([None, '{"count":64,"list":null}']))
            if attrs[0] == "SAI_SWITCH_ATTR_SYSTEM_PORT_CONFIG_LIST":
                return status, SaiData(json.dumps([None, '{"count":256,"list":null}']))
            return status, None
        try:
            result = json.dumps(raw_result)
        except IndexError:
            logging.exception(f'Unable unpack get attrs result for oid: {oid}, key: {key}, obj_type {obj_type} '
                              f'attrs: {attrs} result data: {raw_result}')
            result = '[]'

        if do_assert:
            assert status == 'SAI_STATUS_SUCCESS', f"get({obj}, {attrs}) --> {status}"
            return SaiData(result)

        return status, SaiData(result)

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

    def vid_to_type(self, vid):
        return "SAI_OBJECT_TYPE_" + self.get_object_type(vid).name

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

        attr_kwargs = dict(ThriftConverter.convert_attributes_to_thrift(attrs, obj_type))

        result = sai_thrift_function(self.thrift_client, **object_key, **attr_kwargs)
        status = ThriftConverter.convert_to_sai_status_str(sai_adapter.status)
        if status == 'SAI_STATUS_SUCCESS':
            result = key if key is not None else result
        else:
            result = None
        return status, result

    def _operate_attributes(self, operation, attrs=(), oid=None, obj_type=None, key=None):
        if oid is not None and key is not None:
            raise ValueError('Both oid and key are specified')

        if oid is not None:
            oid = ThriftConverter.object_id(oid)

        if obj_type is None:
            obj_type = self.get_object_type(oid)

        obj_type_name = self.get_object_type(oid, default=obj_type).name.lower()
        object_key = ThriftConverter.convert_key_to_thrift(obj_type_name, key)
        sai_thrift_function = getattr(sai_adapter, f'sai_thrift_{operation}_{obj_type_name}_attribute')

        result = []

        for attr, value in ThriftConverter.convert_attributes_to_thrift(attrs, obj_type):
            if key is None and obj_type_name != "switch":
                object_key = {obj_type_name + "_oid": oid}

            # The function parameter can not start from digit.
            # E.g., 1000x_sgmii_slave_autodetect
            if attr[0].isdigit():
                attr = '_' + attr

            thrift_attr_value = sai_thrift_function(self.thrift_client, **object_key, **{attr: value})

            if operation == 'set':
                # No need to have a list here, since set always takes only one attribute at a time
                status = ThriftConverter.convert_to_sai_status_str(thrift_attr_value)
            else:
                status = ThriftConverter.convert_to_sai_status_str(sai_adapter.status)
                result.extend(ThriftConverter.convert_attributes_from_thrift(thrift_attr_value, obj_type))

        return status, result

    def cleanup(self):
        if self.thrift_transport:
            self.thrift_transport.close()

        # Handle cleanup for saivs target
        if self.config["saivs"]:
            # Handle cleanup for saivs target running in standalone mode
            if self.config["ip"] in ["localhost", "127.0.0.1"]:
                subprocess.run(["supervisorctl", "restart", "saiserver"])
                time.sleep(1)

        # TODO: Handle cleanup in generic way..

        self.thrift_transport = TSocket.TSocket(self.config['ip'], self.config['port'])
        self.thrift_transport = TTransport.TBufferedTransport(self.thrift_transport)
        protocol = TBinaryProtocol.TBinaryProtocol(self.thrift_transport)
        self.thrift_transport.open()
        self.thrift_client = sai_rpc.Client(protocol)

    def flush_fdb_entries(self, obj, attrs=None):
        attr_kwargs = dict(ThriftConverter.convert_attributes_to_thrift(attrs))
        result = sai_adapter.sai_thrift_flush_fdb_entries(self.thrift_client, **attr_kwargs)

    def bulk_create(self, obj_type, keys, attrs, obj_count=0, do_assert=True):
        # TODO: Provide proper implementation once Thrift bulk API is available
        out_keys = []
        entries_num = len(keys) if keys else obj_count
        statuses = [None] * entries_num

        if type(obj_type) == SaiObjType:
            obj_type = "SAI_OBJECT_TYPE_" + obj_type.name

        for i in range(entries_num):
            attr = attrs[0] if len(attrs) == 1 else attrs[i]
            if do_assert == False:
                status, vid = self.create(obj_type + ":" + json.dumps(keys[i]), attr, do_assert)
                out_keys.append(vid)
                statuses.append(status)
                if status != "SAI_STATUS_SUCCESS":
                    return "SAI_STATUS_FAILURE", out_keys, statuses
            else:
                vid = self.create(obj_type + ":" + json.dumps(keys[i]), attr, do_assert)
                out_keys.append(vid)
                statuses.append("SAI_STATUS_SUCCESS")
        return "SAI_STATUS_SUCCESS", out_keys, statuses

    def bulk_remove(self, obj_type, keys, do_assert=True):
        # TODO: Provide proper implementation once Thrift bulk API is available
        statuses = [None] * len(keys)

        if type(obj_type) == SaiObjType:
            obj_type = "SAI_OBJECT_TYPE_" + obj_type.name

        for key in keys:
            if do_assert == False:
                status, _ = self.remove(obj_type + ":" + json.dumps(key), do_assert)
                statuses.append(status)
                if status != "SAI_STATUS_SUCCESS":
                    return "SAI_STATUS_FAILURE", statuses
            else:
                self.remove(obj_type + ":" + json.dumps(key), do_assert)
        return "SAI_STATUS_SUCCESS", statuses

    def bulk_set(self, obj_type, keys, attrs, do_assert=True):
        # TODO: Provide proper implementation once Thrift bulk API is available
        statuses = [None] * len(keys)

        if type(obj_type) == SaiObjType:
            obj_type = "SAI_OBJECT_TYPE_" + obj_type.name

        for i in range(len(keys)):
            attr = attrs[0] if len(attrs) == 1 else attrs[i]
            if do_assert == False:
                status, _ = self.set(obj_type + ":" + json.dumps(keys[i]), attr, do_assert)
                statuses.append(status)
                if status != "SAI_STATUS_SUCCESS":
                    return "SAI_STATUS_FAILURE", statuses
            else:
                self.set(obj_type + ":" + json.dumps(keys[i]), attr, do_assert)
        return "SAI_STATUS_SUCCESS", statuses

    def get_object_key(self, obj_type=None):
        return dict()

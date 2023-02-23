import json
import logging
import os
import pytest

from saichallenger.common.sai_client.sai_client import SaiClient
from saichallenger.common.sai_data import SaiObjType


class CommandProcessor:
    """
    Allow setup scaled configurations with referenced objects.
    Contain reference object cache.
    When objects are referenced they are regenerating missing keys/oids from object cache
    """

    class SubstitutionError(RuntimeError):
        ...

    def __init__(self, sai: 'Sai'):
        self.objects_registry = {}
        self.sai = sai

    def _substitute_from_object_registry(self, obj, *args, **kwargs):
        if isinstance(obj, str) and obj.startswith('$'):
            store_name = obj[1:]
            try:
                return self.objects_registry[store_name]
            except KeyError as e:
                try:
                    return args[0] if args else kwargs['default']
                except KeyError:
                    raise self.SubstitutionError from e
        else:
            raise self.SubstitutionError

    def substitute_command_from_object_registry(self, command):
        substituted_command = {}
        store_name = command.get("name")

        substituted_command['type'] = command.get(
            "type",
            self.objects_registry.get(store_name, dict(type=None))["type"]
        )
        substituted_command['key'] = command.get(
            "key",
            self.objects_registry.get(store_name, dict(key=None))["key"]
        )

        if substituted_command['key'] is None:
            substituted_command['key'] = command.get(
                "key",
                self.objects_registry.get(store_name, dict(oid=None))["oid"]
            )

        # Substitute key
        key = substituted_command['key']
        if key is not None:
            substituted_key = key
            if isinstance(key, dict):
                substituted_key = {}
                for key_name, key_value in key.items():
                    try:
                        obj = self._substitute_from_object_registry(key_value)
                        substituted_key[key_name] = obj['oid'] if obj['oid'] is not None else obj['key']
                    except self.SubstitutionError:
                        substituted_key[key_name] = key_value
            elif isinstance(key, int):
                substituted_key = key
            substituted_command["key"] = substituted_key

        # Substitute attrs
        attributes = command.get("attributes", [])
        if attributes:
            substituted_command["attributes"] = []
            for attr in attributes:
                try:
                    obj = self._substitute_from_object_registry(attr)
                    substituted_key = obj['oid'] if obj['oid'] is not None else obj['key']
                except self.SubstitutionError:
                    substituted_key = attr
                substituted_command["attributes"].append(substituted_key)

        for key in set(command.keys()) - {"key", "attributes"}:
            substituted_command[key] = command[key]
        return substituted_command

    def process_command(self, command):
        '''
        Command examples:
            {
                "OP" : "create",
                "type" : "SAI_OBJECT_TYPE_VIP_ENTRY",
                "key" : {
                    "switch_id" : "$SWITCH_ID",
                    "vip" : "192.168.0.1"
                },
                "attributes" : [ "SAI_VIP_ENTRY_ATTR_ACTION", "SAI_VIP_ENTRY_ACTION_ACCEPT" ]
            }

            {
                "OP" : "create",
                "type" : "SAI_OBJECT_TYPE_DASH_ACL_GROUP",
                "key": "$acl_in_1",
                "attributes" : [ "SAI_DASH_ACL_GROUP_ATTR_IP_ADDR_FAMILY", "SAI_IP_ADDR_FAMILY_IPV4" ]
            },
        '''
        command = self.substitute_command_from_object_registry(command)

        store_name = command.get("name")
        operation = command.get("op", 'create')
        attrs = command.get("attributes", [])
        obj_type = command.get("type")
        obj_key = command.get("key")

        if obj_key is None:
            obj_id = obj_type
        elif type(obj_key) == dict:
            obj_key = json.dumps(obj_key)
            obj_id = obj_type + ":" + obj_key
        elif type(obj_key) == str and obj_key.startswith("oid:0x"):
            obj_id = obj_key
        else:
            assert False, f"Failed to process: {obj_type}, {obj_key}, {operation}"

        if operation == "create":
            obj = self.sai.create(obj_id, attrs)
            if isinstance(store_name, str):  # Store to the DB
                self.objects_registry[store_name] = {
                    "type": obj_type,
                    **(dict(oid=obj, key=None) if obj_key is None else dict(oid=None, key=obj))
                }
            return obj

        elif operation == "remove":
            try:
                return self.sai.remove(obj_id)
            except Exception:
                logging.exception('SAI object removal failed', exc_info=True)
                raise
            finally:
                if store_name is not None:  # remove from the DB
                    del self.objects_registry[store_name]

        elif operation == "get":
            return self.sai.get(obj_id, attrs)

        elif operation == "set":
            return self.sai.set(obj_id, attrs)
        else:
            assert False, f"Unsupported operation: {operation}"


class Sai():
    def __init__(self, cfg):
        self.cfg = cfg.copy()
        self.command_processor = CommandProcessor(self)
        self.libsaivs = cfg.get("target") == "saivs"
        self.run_traffic = cfg["traffic"] and not self.libsaivs
        self.name = cfg.get("asic")
        self.target = cfg.get("target")
        self.sku = cfg.get("sku")
        self.asic_dir = cfg.get("asic_dir")
        self._switch_oid = None

        cfg["client"]["config"]["saivs"] = self.libsaivs
        self.sai_client = SaiClient.spawn(cfg["client"])

    @property
    def switch_oid(self):
        return self._switch_oid

    @switch_oid.setter
    def switch_oid(self, value):
        self.command_processor.objects_registry['SWITCH_ID'] = dict(type='SAI_OBJECT_TYPE_SWITCH', oid=value, key=None)
        self._switch_oid = value

    def process_commands(self, commands):
        yield from map(self.command_processor.process_command, commands)

    def cleanup(self):
        dut = self.cfg.get("dut", None)
        if dut:
            dut.cleanup()
        return self.sai_client.cleanup()

    def set_loglevel(self, sai_api, loglevel):
        return self.sai_client.set_loglevel(sai_api, loglevel)

    # CRUD
    def create(self, obj, attrs, do_assert=True):
        return self.sai_client.create(obj, attrs, do_assert)

    def remove(self, obj, do_assert=True):
        return self.sai_client.remove(obj, do_assert)

    def set(self, obj, attr, do_assert=True):
        return self.sai_client.set(obj, attr, do_assert)

    def get(self, obj, attrs, do_assert=True):
        return self.sai_client.get(obj, attrs, do_assert)

    # BULK (TODO remove do_assert, "oid:" and handle oid
    def bulk_create(self, obj, keys, attrs, do_assert=True):
        return self.sai_client.bulk_create(obj, keys, attrs, do_assert)

    def bulk_remove(self, obj, keys, do_assert=True):
        return self.sai_client.bulk_remove(obj, keys, do_assert)

    def bulk_set(self, obj, keys, attrs, do_assert=True):
        return self.sai_client.bulk_set(obj, keys, attrs, do_assert)

    # Stats
    def get_stats(self, obj, attrs, do_assert=True):
        return self.sai_client.get_stats(obj, attrs, do_assert)

    def clear_stats(self, obj, attrs, do_assert=True):
        return self.sai_client.clear_stats(obj, attrs, do_assert)

    # Flush FDB
    def flush_fdb_entries(self, obj, attrs=None):
        self.sai_client.flush_fdb_entries(obj, attrs)

    # Host interface
    def remote_iface_exists(self, iface):
        return self.sai_client.remote_iface_exists(iface)

    def remote_iface_is_up(self, iface):
        return self.sai_client.remote_iface_is_up(iface)

    def remote_iface_status_set(self, iface, status):
        return self.sai_client.remote_iface_status_set(iface, status)

    def remote_iface_agent_start(self, ifaces):
        return self.sai_client.remote_iface_agent_start(ifaces)

    def remote_iface_agent_stop(self):
        return self.sai_client.remote_iface_agent_stop()

    def vid_to_type(self, vid):
        return self.sai_client.vid_to_type(vid)

    # Used in tests
    @staticmethod
    def get_meta(obj_type=None):
        try:
            path = "/etc/sai/sai.json"
            f = open(path, "r")
            sai_str = f.read()
            sai_json = json.loads(sai_str)
        except IOError:
            return None

        if obj_type is not None:
            if type(obj_type) == SaiObjType:
                obj_type = "SAI_OBJECT_TYPE_" + SaiObjType(obj_type).name
            else:
                assert type(obj_type) == str
                assert obj_type.startswith("SAI_OBJECT_TYPE_")

            for item in sai_json:
                if obj_type in item.values():
                    return item
            else:
                return None
        return sai_json

    @staticmethod
    def get_obj_attrs(sai_obj_type):
        meta = Sai.get_meta(sai_obj_type)
        if meta is None:
            return []
        return [(attr['name'], attr['properties']['type']) for attr in meta['attributes']]

    @staticmethod
    def get_obj_attr_type(sai_obj_type, sai_obj_attr):
        attrs = Sai.get_obj_attrs(sai_obj_type)
        for attr in attrs:
            if attr[0] == sai_obj_attr:
                return attr[1]
        return None

    def get_by_type(self, obj, attr, attr_type, do_assert=False):
        # TODO: Check how to map these types into the struct or list
        unsupported_types = [
                                "sai_port_eye_values_list_t", "sai_prbs_rx_state_t",
                                "sai_port_err_status_list_t", "sai_fabric_port_reachability_t"
                            ]
        if attr_type == "sai_object_list_t":
            status, data = self.get(obj, [attr, "1:oid:0x0"], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                status, data = self.get(obj, [attr, self.make_list(data.uint32(), "oid:0x0")], do_assert)
        elif attr_type == "sai_s32_list_t" or attr_type == "sai_u32_list_t" or \
                attr_type == "sai_s16_list_t" or attr_type == "sai_u16_list_t" or\
                attr_type == "sai_s8_list_t" or attr_type == "sai_u8_list_t" or attr_type == "sai_vlan_list_t":
            status, data = self.get(obj, [attr, "1:0"], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                status, data = self.get(obj, [attr, self.make_list(data.uint32(), "0")], do_assert)
        elif attr_type == "sai_acl_capability_t":
            status, data = self.get(obj, [attr, self.make_acl_list(1)], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                # extract number of actions supported for the stage
                # e.g. ["SAI_SWITCH_ATTR_ACL_STAGE_EGRESS","true:51"] -> 51
                length = int(data.to_json()[1].split(":")[1])
                status, data = self.get(obj, [attr, self.make_acl_list(length)], do_assert)
        elif attr_type == "sai_acl_resource_list_t":
            status, data = self.get(obj, [attr, self.make_acl_resource_list(1)], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                # extract number of actions supported for the stage
                # e.g. ['SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE', '{"count":10,"list":null}'] -> 10
                length = json.loads(data.to_json()[1])["count"]
                status, data = self.get(obj, [attr, self.make_acl_resource_list(length)], do_assert)
        elif attr_type == "sai_map_list_t":
            status, data = self.get(obj, [attr, self.make_map_list(1)], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                length = json.loads(data.to_json()[1])["count"]
                status, data = self.get(obj, [attr, self.make_map_list(length)], do_assert)
        elif attr_type == "sai_system_port_config_list_t":
            status, data = self.get(obj, [attr, self.make_system_port_config_list(1)], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                length = json.loads(data.to_json()[1])["count"]
                status, data = self.get(obj, [attr, self.make_system_port_config_list(length)], do_assert)
        elif attr_type == "sai_object_id_t":
            status, data = self.get(obj, [attr, "oid:0x0"], do_assert)
        elif attr_type == "bool":
            status, data = self.get(obj, [attr, "true"], do_assert)
        elif attr_type == "sai_mac_t":
            status, data = self.get(obj, [attr, "00:00:00:00:00:00"], do_assert)
        elif attr_type == "sai_ip_address_t":
            status, data = self.get(obj, [attr, "0.0.0.0"], do_assert)
        elif attr_type == "sai_ip4_t":
            status, data = self.get(obj, [attr, "0.0.0.0&mask:0.0.0.0"], do_assert)
        elif attr_type == "sai_ip6_t":
            status, data = self.get(obj, [attr, "::0.0.0.0&mask:0:0:0:0:0:0:0:0"], do_assert)
        elif attr_type == "sai_u32_range_t" or attr_type == "sai_s32_range_t":
            status, data = self.get(obj, [attr, "0,0"], do_assert)
        elif attr_type in unsupported_types:
            status, data = "not supported", None
        elif attr_type.startswith("sai_") or attr_type == "" or attr_type == "char":
            status, data = self.get(obj, [attr, ""], do_assert)
        else:
            assert False, f"Unsupported attribute type: get_by_type({obj}, {attr}, {attr_type})"
        return status, data

    def get_list(self, obj, attr, value):
        status, data = self.get(obj, [attr, "1:" + value], False)
        if status == "SAI_STATUS_BUFFER_OVERFLOW":
            in_data = self.make_list(data.uint32(), value)
            data = self.get(obj, [attr, in_data])
        else:
            assert status == 'SAI_STATUS_SUCCESS', f"get_list({obj}, {attr}, {value}) --> {status}"

        return data.to_list()

    def get_object_key(self, obj_type=None):
        return self.sai_client.get_object_key(obj_type)

    def assert_status_success(self, status, skip_not_supported=True, skip_not_implemented=True):
        if skip_not_supported:
            if status == "SAI_STATUS_NOT_SUPPORTED" or status == "SAI_STATUS_ATTR_NOT_SUPPORTED_0":
                pytest.skip("not supported")

        if skip_not_implemented:
            if status == "SAI_STATUS_NOT_IMPLEMENTED" or status == "SAI_STATUS_ATTR_NOT_IMPLEMENTED_0":
                pytest.skip("not implemented")

        assert status == "SAI_STATUS_SUCCESS"

    def make_list(self, length, elem):
        return "{}:".format(length) + (elem + ",") * (length - 1) + elem

    def make_acl_list(self, length):
        return f'false:{self.make_list(length, "0")}'

    def make_acl_resource_list(self, length):
        attr_value = {
            "count": length,
            "list": [{"avail_num": "", "bind_point": "", "stage": ""}] * length
        }
        return json.dumps(attr_value).replace(" ", "")

    def make_map_list(self, length):
        attr_value = {
            "count": length,
            "list": [{"key": 0, "value": 0}] * length
        }
        return json.dumps(attr_value).replace(" ", "")

    def make_system_port_config_list(self, length):
        attr_value = {
            "count": length,
            "list": [{"port_id": "", "attached_switch_id": "", "attached_core_index": "",
                      "attached_core_port_index": "", "speed": "", "num_voq": ""}] * length
        }
        return json.dumps(attr_value).replace(" ", "")

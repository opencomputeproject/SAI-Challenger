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
                "oid",
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
        self.cache = {}
        self.rec2vid = {}

        cfg["client"]["config"]["saivs"] = self.libsaivs
        self.sai_client = SaiClient.spawn(cfg["client"])

    @property
    def switch_oid(self):
        return self._switch_oid

    @switch_oid.setter
    def switch_oid(self, value):
        self.create_alias('SWITCH_ID', 'SAI_OBJECT_TYPE_SWITCH', value)
        self._switch_oid = value

    def process_commands(self, commands, cleanup=False):
        if cleanup:
            cleanup_commands = []
            for command in reversed(commands):
                if command['op'] == 'create':
                    cleanup_commands.append(
                        {
                            'name': command.get('name'),
                            'key': command.get('key'),
                            'op': 'remove'
                        }
                    )
            yield from map(self.command_processor.process_command, cleanup_commands)
        else:
            yield from map(self.command_processor.process_command, commands)

    def alloc_vid(self, obj_type):
        return self.sai_client.alloc_vid(obj_type)

    def get_vid(self, obj_type, value=None):
        if obj_type.name not in self.cache:
            self.cache[obj_type.name] = {}

        if value is None:
            return self.cache[obj_type.name]

        if value in self.cache[obj_type.name]:
            return self.cache[obj_type.name][value]

        oid = self.alloc_vid(obj_type)
        self.cache[obj_type.name][value] = oid
        return oid

    def apply_rec(self, fname):
        dut = self.cfg.get("dut", None)
        if dut:
            dut.cleanup()
        return self.__apply_rec(fname)

    def cleanup(self):
        dut = self.cfg.get("dut", None)
        if dut:
            dut.cleanup()
        self.sai_client.cleanup()
        self.cache = {}
        self.rec2vid = {}

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

    # BULK
    def bulk_create(self, obj_type, keys, attrs, obj_count=0, do_assert=True):
        return self.sai_client.bulk_create(obj_type, keys, attrs, obj_count, do_assert)

    def bulk_remove(self, obj_type, keys, do_assert=True):
        return self.sai_client.bulk_remove(obj_type, keys, do_assert)

    def bulk_set(self, obj_type, keys, attrs, do_assert=True):
        return self.sai_client.bulk_set(obj_type, keys, attrs, do_assert)

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
                                "sai_port_err_status_list_t", "sai_fabric_port_reachability_t",
                                "sai_port_lane_latch_status_list_t", "sai_latch_status_t"
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
            status, data = f"SAI-C internal failure. Unsupported type {attr_type}", None
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

        if status.startswith("SAI-C internal failure"):
            pytest.xfail(status)

        assert status == "SAI_STATUS_SUCCESS", f"Operation failed due to {status}"

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

    def create_alias(self, alias, obj_type, oid, key=None):
        '''
        Create new alias or update existing alias for a given oid or key.
        This alias can be used in data-driven configuration that
        should be applied by process_commands() API.
        '''
        self.command_processor.objects_registry[alias] = dict(type=obj_type, oid=oid, key=key)

    def remove_alias(self, alias):
        '''
        Remove alias.
        '''
        self.command_processor.objects_registry.pop(alias, None)

    def objects_discovery(self):
        '''
        This method discovers existing objects and
        creates the aliases as follows:
            DEFAULT_1Q_BRIDGE_ID
            DEFAULT_VLAN_ID
            DEFAULT_VIRTUAL_ROUTER_ID
            PORT_{idx}
            BRIDGE_PORT_{idx}
        '''
        dot1q_br_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]).oid()
        self.create_alias('DEFAULT_1Q_BRIDGE_ID', 'SAI_OBJECT_TYPE_BRIDGE', dot1q_br_oid)
        oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "oid:0x0"]).oid()
        self.create_alias('DEFAULT_VLAN_ID', 'SAI_OBJECT_TYPE_VLAN', oid)
        oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).oid()
        self.create_alias('DEFAULT_VIRTUAL_ROUTER_ID', 'SAI_OBJECT_TYPE_VIRTUAL_ROUTER', oid)

        port_num = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            port_oids = self.get(self.switch_oid,
                                 ["SAI_SWITCH_ATTR_PORT_LIST", self.make_list(port_num, "oid:0x0")]).oids()
            for idx, oid in enumerate(port_oids):
                self.create_alias(f"PORT_{idx}", 'SAI_OBJECT_TYPE_PORT', oid)


            status, data = self.get(dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST", "1:oid:0x0"], False)
            bport_num = data.uint32()
            assert (status == "SAI_STATUS_BUFFER_OVERFLOW")
            assert (bport_num > 0)

            dot1q_bp_oids = self.get(dot1q_br_oid,
                                     ["SAI_BRIDGE_ATTR_PORT_LIST", self.make_list(bport_num, "oid:0x0")]).oids()
            for idx, oid in enumerate(dot1q_bp_oids):
                self.create_alias(f"BRIDGE_PORT_{idx}", 'SAI_OBJECT_TYPE_BRIDGE_PORT', oid)

    def __apply_rec(self, fname):
        # Since it's expected that sairedis.rec file contains a full configuration,
        # we must flush both Redis and NPU state before we start.
        self.cleanup()

        oids = []
        records = self.__parse_rec(fname)
        for cnt, record in records.items():
            print("#{}: {}".format(cnt, record))
            rec = record[0]
            if rec[0] == 'c':
                attrs = []
                if len(rec) > 2:
                    for attr in rec[2:]:
                        attrs += attr.split('=')

                # Update OIDs in the attributes
                for idx in range(1, len(attrs), 2):
                    if "oid:" in attrs[idx]:
                        attrs[idx] = self.rec2vid[attrs[idx]]

                self.create(self.__update_key(rec[0], rec[1]), attrs)

            elif rec[0] == 'C':
                # record = [["action", "sai-object-type"], ["key", "attr1", "attr2"], ..., [key-n", "attr1", "attr2"]]
                bulk_keys = []
                bulk_attrs = []
                for idx, entry in enumerate(record[1:]):
                    # New bulk entry
                    attrs = []
                    for attr in entry[1:]:
                        attrs += attr.split('=')

                    # Update OIDs in the attributes
                    for i in range(1, len(attrs), 2):
                        if "oid:" in attrs[i] and attrs[i] != "oid:0x0":
                            attrs[i] = self.rec2vid[attrs[i]]

                    # Convert into "sai-object-type:key"
                    key = record[0][1] + ":" + record[idx + 1][0]
                    # Update OIDs in the key
                    key = self.__update_key(rec[0], key)
                    # Convert into ["sai-object-type", "key"]
                    key = key.split(":", 1)[1]

                    if key.startswith("{"):
                        key = json.loads(key)
                    bulk_keys.append(key)
                    bulk_attrs.append(attrs)

                self.bulk_create(record[0][1], bulk_keys, bulk_attrs)

            elif rec[0] == 's':
                data = rec[2].split('=')
                if "oid:" in data[1]:
                    data[1] = self.rec2vid[data[1]]

                self.set(self.__update_key(rec[0], rec[1]), data)

            elif rec[0] == 'S':
                # record = [["action", "sai-object-type"], ["key", "attr"], ..., [key-n", "attr"]]
                bulk_keys = []
                bulk_attrs = []
                for idx, entry in enumerate(record[1:]):
                    attr = entry[1].split('=')
                    if "oid:" in attr[1] and attrs[i] != "oid:0x0":
                        attr[1] = self.rec2vid[attr[1]]

                    # Convert into "sai-object-type:key"
                    key = record[0][1] + ":" + record[idx + 1][0]
                    # Update OIDs in the key
                    key = self.__update_key(rec[0], key)
                    # Convert into ["sai-object-type", "key"]
                    key = key.split(":", 1)[1]

                    if key.startswith("{"):
                        key = json.loads(key)
                    bulk_keys.append(key)
                    bulk_attrs.append(attr)

                self.bulk_set(record[0][1], bulk_keys, bulk_attrs)

            elif rec[0] == 'r':
                self.remove(self.__update_key(rec[0], rec[1]))

            elif rec[0] == 'R':
                # record = [["action", "sai-object-type"], ["key"], ..., [key-n"]]
                bulk_keys = []
                for idx, entry in enumerate(record[1:]):
                    # Convert into "sai-object-type:key"
                    key = record[0][1] + ":" + record[idx + 1][0]
                    # Update OIDs in the key
                    key = self.__update_key(rec[0], key)
                    # Convert into ["sai-object-type", "key"]
                    key = key.split(":", 1)[1]

                    if key.startswith("{"):
                        key = json.loads(key)
                    bulk_keys.append(key)

                self.bulk_remove(record[0][1], bulk_keys)

            elif rec[0] == 'g':
                attrs = []
                if len(rec) > 2:
                    for attr in rec[2:]:
                        attrs += attr.split('=')

                status, data = self.get(self.__update_key(rec[0], rec[1]), attrs, False)
                if status == "SAI_STATUS_SUCCESS":
                    jdata = data.to_json()
                    for idx in range(1, len(jdata), 2):
                        if ":oid:" in jdata[idx]:
                            oids += data.oids(idx)
                        elif "oid:" in jdata[idx]:
                            oids.append(data.oid(idx))
            elif rec[0] == 'G':
                attrs = []
                for attr in rec[2:]:
                    attrs += attr.split('=')

                G_oids = []

                for idx in range(1, len(attrs), 2):
                    G_output = attrs[idx]

                    if ":oid:" in G_output:
                        start_idx = G_output.find(":") + 1
                        G_oids += G_output[start_idx:].split(",")
                    elif "oid:" in G_output:
                        G_oids.append(G_output)
                assert len(oids) == len(G_oids)

                for idx, oid in enumerate(G_oids):
                    self.rec2vid[oid] = oids[idx]
                oids = []
            else:
                print("Iggnored line {}: {}".format(cnt, rec))

        print("Current SAI objects: {}".format(self.rec2vid))

    def __update_oid_key(self, action, key):
        key_list = key.split(":", 1)
        vid = key_list[1]

        if action == "c" or action == "C":
            # Convert object type from string to enum format
            obj_type = SaiObjType[key_list[0][len("SAI_OBJECT_TYPE_"):]]
            # Allocate new VID and add it to the map
            vid = self.get_vid(obj_type, key_list[1])
            self.rec2vid[key_list[1]] = vid
        elif action == "g" or action == "s" or action == "S":
            vid = self.rec2vid[key_list[1]]
        elif action == "r" or action == "R":
            vid = self.rec2vid.pop(key_list[1])

        return key_list[0] + ":" + vid

    def __update_entry_key_oids(self, key):
        oids = []
        new_key = key
        key_list = key.split("\"")
        for k in key_list:
            if "oid:" in k:
                oids.append(k)
        for oid in oids:
            new_oid = self.rec2vid[oid]
            new_key = new_key.replace(oid, new_oid)
        return new_key

    def __update_key(self, action, key):
        if "{" in key:
            return self.__update_entry_key_oids(key)
        else:
            return self.__update_oid_key(action, key)

    def __parse_rec(self, fname):
        '''
        Non-bulk entry format:
        data|action|sai-object-type:key|attr1|attr2

        Will be converted into:
        [["action", "sai-object-type:key", "attr1", "attr2"]]

        Bulk entry format:
        data|action|sai-object-type||key1|attr1|attr2||...||key-n|attr1|attr2

        Will be converted into:
        [["action", "sai-object-type"], ["key", "attr1", "attr2"], ..., [key-n", "attr1", "attr2"]]
        '''
        cnt = 0
        rec = {}
        fp = open(fname, 'r')
        for line in fp:
            data = []
            cnt += 1
            bulk_tokens = line.strip().split("||")
            for idx, token in enumerate(bulk_tokens):
                tokens = token.strip().split("|")
                if idx == 0:
                    tokens = tokens[1:]
                data.append(tokens)
            rec[cnt] = data #if len(data) > 1 else data[0]
        return rec

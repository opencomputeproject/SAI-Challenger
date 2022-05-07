from enum import Enum
import redis
import time
import json
import os
import pytest


class SaiObjType(Enum):
    PORT                     =  1
    LAG                      =  2
    VIRTUAL_ROUTER           =  3
    NEXT_HOP                 =  4
    NEXT_HOP_GROUP           =  5
    ROUTER_INTERFACE         =  6
    ACL_TABLE                =  7
    ACL_ENTRY                =  8
    ACL_COUNTER              =  9
    ACL_RANGE                = 10
    ACL_TABLE_GROUP          = 11
    ACL_TABLE_GROUP_MEMBER   = 12
    HOSTIF                   = 13
    MIRROR_SESSION           = 14
    SAMPLEPACKET             = 15
    STP                      = 16
    HOSTIF_TRAP_GROUP        = 17
    POLICER                  = 18
    WRED                     = 19
    QOS_MAP                  = 20
    QUEUE                    = 21
    SCHEDULER                = 22
    SCHEDULER_GROUP          = 23
    BUFFER_POOL              = 24
    BUFFER_PROFILE           = 25
    INGRESS_PRIORITY_GROUP   = 26
    LAG_MEMBER               = 27
    HASH                     = 28
    UDF                      = 29
    UDF_MATCH                = 30
    UDF_GROUP                = 31
    FDB_ENTRY                = 32
    SWITCH                   = 33
    HOSTIF_TRAP              = 34
    HOSTIF_TABLE_ENTRY       = 35
    NEIGHBOR_ENTRY           = 36
    ROUTE_ENTRY              = 37
    VLAN                     = 38
    VLAN_MEMBER              = 39
    HOSTIF_PACKET            = 40
    TUNNEL_MAP               = 41
    TUNNEL                   = 42
    TUNNEL_TERM_TABLE_ENTRY  = 43
    FDB_FLUSH                = 44
    NEXT_HOP_GROUP_MEMBER    = 45
    STP_PORT                 = 46
    RPF_GROUP                = 47
    RPF_GROUP_MEMBER         = 48
    L2MC_GROUP               = 49
    L2MC_GROUP_MEMBER        = 50
    IPMC_GROUP               = 51
    IPMC_GROUP_MEMBER        = 52
    L2MC_ENTRY               = 53
    IPMC_ENTRY               = 54
    MCAST_FDB_ENTRY          = 55
    HOSTIF_USER_DEFINED_TRAP = 56
    BRIDGE                   = 57
    BRIDGE_PORT              = 58
    TUNNEL_MAP_ENTRY         = 59
    TAM                      = 60
    SRV6_SIDLIST             = 61
    PORT_POOL                = 62
    INSEG_ENTRY              = 63
    DTEL                     = 64
    DTEL_QUEUE_REPORT        = 65
    DTEL_INT_SESSION         = 66
    DTEL_REPORT_SESSION      = 67
    DTEL_EVENT               = 68
    BFD_SESSION              = 69
    ISOLATION_GROUP          = 70
    ISOLATION_GROUP_MEMBER   = 71
    TAM_MATH_FUNC            = 72
    TAM_REPORT               = 73
    TAM_EVENT_THRESHOLD      = 74
    TAM_TEL_TYPE             = 75
    TAM_TRANSPORT            = 76
    TAM_TELEMETRY            = 77
    TAM_COLLECTOR            = 78
    TAM_EVENT_ACTION         = 79
    TAM_EVENT                = 80
    NAT_ZONE_COUNTER         = 81
    NAT_ENTRY                = 82
    TAM_INT                  = 83
    COUNTER                  = 84
    DEBUG_COUNTER            = 85
    PORT_CONNECTOR           = 86
    PORT_SERDES              = 87
    MACSEC                   = 88
    MACSEC_PORT              = 89
    MACSEC_FLOW              = 90
    MACSEC_SC                = 91
    MACSEC_SA                = 92
    SYSTEM_PORT              = 93
    FINE_GRAINED_HASH_FIELD  = 94
    SWITCH_TUNNEL            = 95
    MY_SID_ENTRY             = 96
    MY_MAC                   = 97
    NEXT_HOP_GROUP_MAP       = 98
    IPSEC                    = 99
    IPSEC_PORT               = 100
    IPSEC_SA                 = 101


class SaiData:
    def __init__(self, data):
        self.data = data

    def raw(self):
        return self.data

    def to_json(self):
        return json.loads(self.data)

    def oid(self, idx = 1):
        value = self.to_json()[idx]
        if "oid:" in value:
            return value
        return "oid:0x0"

    def to_list(self, idx = 1):
        value = self.to_json()[idx]
        idx = value.index(":") + 1
        return value[idx:].split(",")

    def oids(self, idx = 1):
        value = self.to_list(idx)
        if len(value) > 0:
            if "oid:" in value[0]:
                return value
        return []

    def counters(self):
        i = 0
        cntrs_dict = {}
        value = self.to_json()
        while i < len(value):
            cntrs_dict[value[i]] = int(value[i + 1])
            i = i + 2
        return cntrs_dict

    def value(self):
        return self.to_json()[1]

    def uint32(self):
        return int(self.value())


class Sai:

    attempts = 40

    def __init__(self, exec_params):
        self.server_ip = exec_params["server"]
        self.loglevel = exec_params["loglevel"]
        self.r = redis.Redis(host=self.server_ip, port=6379, db=1)
        self.loglevel_db = redis.Redis(host=self.server_ip, port=6379, db=3)
        self.cache = {}
        self.rec2vid = {}

        self.client_mode = not os.path.isfile("/usr/bin/redis-server")
        libsai = os.path.isfile("/usr/lib/libsai.so") or os.path.isfile("/usr/local/lib/libsai.so")
        self.libsaivs = exec_params["saivs"] or (not self.client_mode and not libsai)
        self.run_traffic = exec_params["traffic"] and not self.libsaivs
        self.sku = exec_params["sku"]

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

    def cleanup(self):
        '''
        Flushes Redis DB and restarts syncd application.

        Each time SAI Challenger starts TCs execution, it's expected that
        the system (DUT) is in the initial state with no extra SAI objects
        created. To ensure this, the framework should flush Redis DB content
        and restart syncd application linked with SAI library.

        The execution flow:
          1. On Docker start, the supervisord starts Redis server and syncd.
             For more details, please see `supervisord.conf` file.
          2. This function flushes Redis DB content by FLUSHALL command
             and then stops Redis server by SHUTDOWN command.
          3. The supervisord restarts Redis program as per `autorestart`
             option in `supervisord.conf` file.
          4. As a part of Redis program `command` option, supervisord
             restarts syncd through `killall syncd` command.
          5. The supervisord restarts syncd program as per `autorestart`
             option in `supervisord.conf` file.
        '''
        self.r.flushall()
        self.loglevel_db.hmset('syncd:syncd', {'LOGLEVEL':self.loglevel, 'LOGOUTPUT':'SYSLOG'})
        self.r.shutdown()
        self.cache = {}
        self.rec2vid = {}

    def alloc_vid(self, obj_type):
        vid = None
        if obj_type == SaiObjType.SWITCH:
            if self.r.get("VIDCOUNTER") is None:
                self.r.set("VIDCOUNTER", 0)
                vid = 0
        if vid is None:
            vid = self.r.incr("VIDCOUNTER")
        return "oid:" + hex((obj_type.value << 48) | vid)

    @staticmethod
    def vid_to_type(vid):
        obj_type = int(vid[4:], 16) >> 48
        return "SAI_OBJECT_TYPE_" + SaiObjType(obj_type).name

    def vid_to_rid(self, vid):
        assert vid.startswith("oid:"), f"Invalid VID format {vid}"
        rid = self.r.hget("VIDTORID", vid)
        if rid is not None:
            rid = rid.decode("utf-8")
            assert rid.startswith("oid:"), f"Invalid RID format {vid}"
        return rid

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

    def pop_vid(self, obj_type, value):
        if obj_type.name in self.cache:
            return self.cache[obj_type.name].pop(value, "")
        return ""

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

    def operate(self, obj, attrs, op):
        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        tout = 0.03
        attempts = self.attempts
        while len(self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)) > 0 and attempts > 0:
            time.sleep(0.01)
            attempts -= 1

        if attempts == 0:
            return []

        # Remove spaces from the key string.
        # Required by sai_serialize_route_entry() in sairedis.
        obj = obj.replace(' ', '')

        self.r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", obj, attrs, op)
        self.r.publish("ASIC_STATE_CHANNEL@1", "G")

        status = []
        attempts = self.attempts

        # Wait upto 3 mins for switch init on HW
        if not self.libsaivs and obj.startswith("SAI_OBJECT_TYPE_SWITCH") and op == "Screate":
            tout = 0.5
            attempts = 240

        while len(status) < 3 and attempts > 0:
            time.sleep(tout)
            attempts -= 1
            status = self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)

        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        assert len(status) == 3, "SAI \"{}\" operation failure!".format(op)
        return status

    def create(self, obj, attrs, do_assert = True):
        vid = None
        if type(obj) == SaiObjType:
            vid = self.alloc_vid(obj)
            obj = "SAI_OBJECT_TYPE_" + obj.name + ":" + vid
        else:
            # NOTE: The sai_deserialize_route_entry() from sonic-sairedis does not tolerate
            # spaces in the route entry key:
            # {"dest":"0.0.0.0/0","switch_id":"oid:0x21000000000000","vr":"oid:0x3000000000022"}
            # For more details, please refer to sai_deserialize_route_entry() implementation.
            obj = obj.replace(" ", "")
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Screate")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS', f"create({obj}, {attrs}) --> {status}"
            return vid

        return status[2], vid

    def remove(self, obj, do_assert = True):
        if obj.startswith("oid:"):
            assert self.vid_to_rid(obj), f"Unable to retrieve RID by VID {obj}"
            obj = self.vid_to_type(obj) + ":" + obj
        assert obj.startswith("SAI_OBJECT_TYPE_")
        obj = obj.replace(" ", "")

        status = self.operate(obj, "{}", "Dremove")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS', f"remove({obj}) --> {status}"
        return status[2]

    def set(self, obj, attr, do_assert = True):
        if obj.startswith("oid:"):
            assert self.vid_to_rid(obj), f"Unable to retrieve RID by VID {obj}"
            obj = self.vid_to_type(obj) + ":" + obj
        assert obj.startswith("SAI_OBJECT_TYPE_")
        obj = obj.replace(" ", "")

        if type(attr) != str:
            attr = json.dumps(attr)
        status = self.operate(obj, attr, "Sset")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS', f"set({obj}, {attr}) --> {status}"
        return status[2]

    def get(self, obj, attrs, do_assert = True):
        if obj.startswith("oid:"):
            assert self.vid_to_rid(obj), f"Unable to retrieve RID by VID {obj}"
            obj = self.vid_to_type(obj) + ":" + obj
        assert obj.startswith("SAI_OBJECT_TYPE_")
        obj = obj.replace(" ", "")

        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sget")
        status[2] = status[2].decode("utf-8")

        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS', f"get({obj}, {attrs}) --> {status}"

        data = SaiData(status[1].decode("utf-8"))
        if do_assert:
            return data

        return status[2], data

    def __bulk_attr_serialize(self, attr):
        data = ""
        # Input attributes: [a, v, a, v, ...]
        # Serialized attributes format: "a=v|a=v|..."
        for i, v in enumerate(attr):
            if i % 2 == 0:
                if len(data) > 0:
                    data += "|"
                data += v + "="
            else:
                data += v
        return data

    def bulk_create(self, obj, keys, attrs, do_assert = True):
        '''
        Bulk create objects

        Parameters:
            obj (SaiObjType): The type of objects to be created
            keys (list): The list of objects to be created.
                    E.g.:
                    [
                        {
                            "bvid"      : vlan_oid,
                            "mac"       : "00:00:00:00:00:01",
                            "switch_id" : self.sw_oid
                        },
                        {...}
                    ]
            attrs (list): The list of the lists of objects' attributes.
                    In case just one set of the attributes provided, all objects
                    will be created with this set of the attributes.
                    E.g.:
                    [
                        [
                            "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                            "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", self.sw.dot1q_bp_oids[0]
                        ],
                        [...]
                    ]
            do_assert (bool): Assert that the bulk create operation succeeded.

        Usage example:
            bulk_create(SaiObjType.FDB_ENTRY, [key1, key2, ...], [attrs1, attrs2, ...])
            bulk_create(SaiObjType.FDB_ENTRY, [key1, key2, ...], [attrs])

            where, attrsN = [attr1, val1, attr2, val2, ...]

        Returns:
            The tuple with two elements.
            The first element contains bulk create operation status:
                * "SAI_STATUS_SUCCESS" on success when all objects were created;
                * "SAI_STATUS_FAILURE" when any of the objects fails to create;
            The second element contains the list of statuses of each individual object
            creation result.
        '''
        assert (type(obj) == SaiObjType) or (type(obj) == str and obj.startswith("SAI_OBJECT_TYPE_"))
        assert len(keys) == len(attrs) or len(attrs) == 1

        key = "SAI_OBJECT_TYPE_" + obj.name if type(obj) == SaiObjType else obj
        key = key + ":" + str(len(keys))

        str_attr = ""
        if (len(attrs) == 1):
            str_attr = self.__bulk_attr_serialize(attrs[0])

        values = []
        for i, _ in enumerate(keys):
            k = keys[i]
            if type(k) != str:
                k = json.dumps(k).replace(" ", "")
            values.append(k)
            if (len(attrs) > 1):
                str_attr = self.__bulk_attr_serialize(attrs[i])
            values.append(str_attr)

        status = self.operate(key, json.dumps(values), "Sbulkcreate")

        status[1] = status[1].decode("utf-8")
        status[1] = json.loads(status[1])
        entry_status = []
        for i, v in enumerate(status[1]):
            if i % 2 == 0:
                entry_status.append(v)

        status[2] = status[2].decode("utf-8")

        if do_assert:
            print(entry_status)
            assert status[2] == 'SAI_STATUS_SUCCESS'
            return status[2], entry_status

        return status[2], entry_status

    def bulk_remove(self, obj, keys, do_assert = True):
        '''
        Bulk remove objects

        Parameters:
            obj (SaiObjType): The type of objects to be removed
            keys (list): The list of objects to be removed.
                    E.g.:
                    [
                        {
                            "bvid"      : vlan_oid,
                            "mac"       : "00:00:00:00:00:01",
                            "switch_id" : self.sw_oid
                        },
                        {...}
                    ]
            do_assert (bool): Assert that the bulk remove operation succeeded.

        Usage example:
            bulk_remove(SaiObjType.FDB_ENTRY, [key1, key2, ...])
            bulk_remove(SaiObjType.FDB_ENTRY, [key1, key2, ...], False)

        Returns:
            The tuple with two elements.
            The first element contains bulk remove operation status:
                * "SAI_STATUS_SUCCESS" on success when all objects were removed;
                * "SAI_STATUS_FAILURE" when any of the objects fails to remove;
            The second element contains the list of statuses of each individual object
            removal result.
        '''
        assert (type(obj) == SaiObjType) or (type(obj) == str and obj.startswith("SAI_OBJECT_TYPE_"))

        key = "SAI_OBJECT_TYPE_" + obj.name if type(obj) == SaiObjType else obj
        key = key + ":" + str(len(keys))

        values = []
        for i, _ in enumerate(keys):
            k = keys[i]
            if type(k) != str:
                k = json.dumps(k).replace(" ", "")
            values.append(k)
            values.append("")

        status = self.operate(key, json.dumps(values), "Dbulkremove")

        status[1] = status[1].decode("utf-8")
        status[1] = json.loads(status[1])
        entry_status = []
        for i, v in enumerate(status[1]):
            if i % 2 == 0:
                entry_status.append(v)

        status[2] = status[2].decode("utf-8")

        if do_assert:
            print(entry_status)
            assert status[2] == 'SAI_STATUS_SUCCESS'
            return status[2], entry_status

        return status[2], entry_status

    def bulk_set(self, obj, keys, attrs, do_assert = True):
        '''
        Bulk set objects attribute

        Parameters:
            obj (SaiObjType): The type of objects to be updated
            keys (list): The list of objects to be updated.
                    E.g.:
                    [
                        {
                            "bvid"      : vlan_oid,
                            "mac"       : "00:00:00:00:00:01",
                            "switch_id" : self.sw_oid
                        },
                        {...}
                    ]
            attrs (list): The list of objects' attributes, one attribute per object.
                    In case just one attribute provided, all objects
                    will be updated with the provided value of this attribute.
                    E.g.:
                    [
                        "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                        "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_DYNAMIC",
                        ...
                    ]
            do_assert (bool): Assert that the bulk set operation succeeded.

        Usage example:
            bulk_set(SaiObjType.FDB_ENTRY, [key1, key2, ...], [attr1, attr2, ...])
            bulk_set(SaiObjType.FDB_ENTRY, [key1, key2, ...], [attr])

        Returns:
            The tuple with two elements.
            The first element contains bulk set operation status:
                * "SAI_STATUS_SUCCESS" on success when all objects were updated;
                * "SAI_STATUS_FAILURE" when any of the objects fails to update;
            The second element contains the list of statuses of each individual object
            set attribute result.
        '''
        assert (type(obj) == SaiObjType) or (type(obj) == str and obj.startswith("SAI_OBJECT_TYPE_"))
        assert len(keys) == len(attrs) or len(attrs) == 1

        key = "SAI_OBJECT_TYPE_" + obj.name if type(obj) == SaiObjType else obj
        key = key + ":" + str(len(keys))

        str_attr = ""
        if (len(attrs) == 1):
            str_attr = self.__bulk_attr_serialize(attrs[0])

        values = []
        for i, _ in enumerate(keys):
            k = keys[i]
            if type(k) != str:
                k = json.dumps(k).replace(" ", "")
            values.append(k)
            if (len(attrs) > 1):
                str_attr = self.__bulk_attr_serialize(attrs[i])
            values.append(str_attr)

        status = self.operate(key, json.dumps(values), "Sbulkset")

        status[1] = status[1].decode("utf-8")
        status[1] = json.loads(status[1])
        entry_status = []
        for i, v in enumerate(status[1]):
            if i % 2 == 0:
                entry_status.append(v)

        status[2] = status[2].decode("utf-8")

        if do_assert:
            print(entry_status)
            assert status[2] == 'SAI_STATUS_SUCCESS'
            return status[2], entry_status

        return status[2], entry_status

    def get_by_type(self, obj, attr, attr_type, do_assert = True):
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

    def get_oids(self, obj_type=None):
        oids = []
        all_oids = []
        oids_by_type = dict()

        data = self.r.hgetall("VIDTORID")
        for key, value in data.items():
            all_oids.append(key.decode("utf-8"))

        if obj_type is None:
            all_oids.sort()
            for idx, oid in enumerate(all_oids):
                obj_type = SaiObjType(int(oid[4:], 16) >> 48)
                if obj_type.name not in oids_by_type:
                    oids_by_type[obj_type.name] = list()
                oids_by_type[obj_type.name].append(oid)

            return oids_by_type

        for oid in all_oids:
            if obj_type == SaiObjType(int(oid[4:], 16) >> 48):
                oids.append(oid)
        oids.sort()
        oids_by_type[obj_type.name] = oids
        return oids_by_type

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

    def apply_rec(self, fname):
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

    def assert_status_success(self, status, skip_not_supported=True, skip_not_implemented=True):
        if skip_not_supported:
            if status == "SAI_STATUS_NOT_SUPPORTED" or status == "SAI_STATUS_ATTR_NOT_SUPPORTED_0":
                pytest.skip("not supported")

        if skip_not_implemented:
            if status == "SAI_STATUS_NOT_IMPLEMENTED" or status == "SAI_STATUS_ATTR_NOT_IMPLEMENTED_0":
                pytest.skip("not implemented")

        assert status == "SAI_STATUS_SUCCESS"

    def remote_cmd_operate(self, cmd, args=None):
        self.r.delete("SAI_CHALLENGER_CMD_QUEUE")
        self.r.delete("SAI_CHALLENGER_CMD_STATUS_QUEUE")
        if args is not None:
            if type(args) != str:
                args = json.dumps(args)
            self.r.rpush("SAI_CHALLENGER_CMD_QUEUE", cmd, args)
        else:
            print(cmd)
            self.r.rpush("SAI_CHALLENGER_CMD_QUEUE", cmd)

        status = []
        tout = 0.05
        attempts = self.attempts

        while len(status) == 0 and attempts > 0:
            time.sleep(tout)
            attempts -= 1
            status = self.r.lrange("SAI_CHALLENGER_CMD_STATUS_QUEUE", 0, -1)

        self.r.delete("SAI_CHALLENGER_CMD_STATUS_QUEUE")
        return status[0].decode("utf-8") if len(status) > 0 else "err"

    def remote_iface_exists(self, iface):
        return self.remote_cmd_operate("iface_exists", iface) == "ok"

    def remote_iface_is_up(self, iface):
        return self.remote_cmd_operate("iface_is_up", iface) == "ok"

    def remote_iface_status_set(self, iface, status):
        admin = "up" if status else "down"
        args = {
            "iface": iface,
            "admin": admin
        }
        return self.remote_cmd_operate("set_iface_status", args) == "ok"

    def remote_iface_agent_start(self, ifaces):
        return self.remote_cmd_operate("start_nn_agent", ifaces) == "ok"

    def remote_iface_agent_stop(self):
        return self.remote_cmd_operate("stop_nn_agent") == "ok"

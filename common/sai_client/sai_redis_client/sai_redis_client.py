import json
import redis
import time
import os

from saichallenger.common.sai_client.sai_client import SaiClient
from saichallenger.common.sai_data import SaiObjType, SaiData


class SaiRedisClient(SaiClient):
    """Redis SAI client implementation to wrap low level SAI calls"""
    attempts = 100

    def __init__(self, cfg):
        self.config = cfg
        self.server_ip = cfg["ip"]
        self.loglevel = cfg["loglevel"]
        self.port = cfg["port"]
        self.libsaivs = cfg["saivs"]
        self.asic_channel = None
        self.asic_db = 9 if cfg["asic_type"] is "phy" else 1

        self.is_dut_mbr = cfg.get("mode") is not None

        self.r = redis.Redis(host=self.server_ip, port=self.port, db=self.asic_db)
        self.loglevel_db = redis.Redis(host=self.server_ip, port=self.port, db=3)

    def cleanup(self):
        '''
        Flushes Redis DB and restarts syncd application.

        Each time SAI Challenger starts TCs execution, it's expected that
        the system (DUT) is in the initial state with no extra SAI objects
        created. To ensure this, the framework should flush Redis DB content
        and restart syncd application linked with SAI library.
        '''
        if self.is_dut_mbr:
            self.__assert_syncd_running()
            return

        '''
        SAI-C server environment's flow:
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
        self.assert_process_running(self.port, self.server_ip, "Redis server has not started yet...")
        self.r.flushall()
        self.loglevel_db.hset('syncd:syncd', mapping={'LOGLEVEL':self.loglevel, 'LOGOUTPUT':'SYSLOG'})
        self.r.shutdown()
        time.sleep(1)
        self.assert_process_running(self.port, self.server_ip, "Redis server has not restarted yet...")
        self.__assert_syncd_running()

    def set_loglevel(self, sai_api, loglevel):
        '''
        Sets the logging level for SAI APIs (sai_api_t)

        Parameters:
            sai_api (str): The SAI API (sai_api_t) in string representation.
                           Both short and long form is supported.
            loglevel (str): The SAI log level (sai_log_level_t) in string representation.
                           Both short and long form is supported. The list of supported
                           log levels in short form of representation:
                           DEBUG, INFO, NOTICE, WARN, ERROR, CRITICAL.
        '''
        if not sai_api.startswith("SAI_API_"):
            sai_api = "SAI_API_" + sai_api

        if not loglevel.startswith("SAI_LOG_LEVEL_"):
            loglevel = "SAI_LOG_LEVEL_" + loglevel

        self.loglevel_db.sadd(sai_api + "_KEY_SET", sai_api)
        self.loglevel_db.hset("_" + sai_api + ":" + sai_api, "LOGLEVEL", loglevel)
        self.loglevel_db.publish(sai_api + "_CHANNEL", "G")
        self.loglevel_db.publish(sai_api + "_CHANNEL@3", "G")

    def operate(self, obj, attrs, op):
        if self.asic_channel is None:
            self.__assert_syncd_running()

        # Clean-up Redis RPC I/O pipe
        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")
        status = self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)
        assert len(status) == 0, "Redis RPC I/O failure!"

        # Remove spaces from the key string.
        # Required by sai_deserialize_route_entry() in sonic-sairedis.
        obj = obj.replace(' ', '')
        if "bv_id" in obj:
            obj = obj.replace("bv_id", "bvid")
            obj = obj.replace("mac_address", "mac")

        self.r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", obj, attrs, op)
        self.r.publish(self.asic_channel, "G")

        if obj.startswith("SAI_OBJECT_TYPE_SWITCH") and op == "Screate":
            # Wait upto 3 mins for switch init
            tout = 0.5
            attempts = 240
        else:
            tout = 0.01
            attempts = self.attempts

        # Get response
        status = self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)
        while len(status) < 3 and attempts > 0:
            assert self.__check_syncd_running(), "FATAL - SyncD has exited or crashed!"
            time.sleep(tout)
            attempts -= 1
            status = self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)

        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        assert len(status) == 3, f"SAI \"{op[1:]}\" operation failure!"
        return status

    def create(self, obj, attrs, do_assert=True):
        vid = None
        if type(obj) == SaiObjType:
            vid = self.alloc_vid(obj)
            obj = "SAI_OBJECT_TYPE_" + obj.name + ":" + vid
        elif type(obj) == str and obj.startswith("SAI_OBJECT_TYPE_") and ":" not in obj:
            vid = self.alloc_vid(obj)
            obj = obj + ":" + vid
        else:
            # Key-based objects (route, fdb, nat, etc.)
            vid = json.loads(obj.split(":", 1)[1])

        if type(attrs) != str:
            for i, attr in enumerate(attrs):
                if type(attr) != str:
                    attrs[i] = json.dumps(attr)
            attrs = json.dumps(attrs)

        status = self.operate(obj, attrs, "Screate")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS', f"create({obj}, {attrs}) --> {status}"
            return vid

        return status[2], vid

    def remove(self, obj, do_assert=True):
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

    def set(self, obj, attr, do_assert=True):
        if obj.startswith("oid:"):
            assert self.vid_to_rid(obj), f"Unable to retrieve RID by VID {obj}"
            obj = self.vid_to_type(obj) + ":" + obj
        assert obj.startswith("SAI_OBJECT_TYPE_")

        if type(attr) != str:
            attr = json.dumps(attr)
        status = self.operate(obj, attr, "Sset")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS', f"set({obj}, {attr}) --> {status}"
        return status[2]

    def get(self, obj, attrs, do_assert=True):
        if obj.startswith("oid:"):
            assert self.vid_to_rid(obj), f"Unable to retrieve RID by VID {obj}"
            obj = self.vid_to_type(obj) + ":" + obj
        assert obj.startswith("SAI_OBJECT_TYPE_")

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

    def bulk_create(self, obj_type, keys, attrs, obj_count=0, do_assert=True):
        '''
        Bulk create objects
        Parameters:
            obj_type (SaiObjType): The type of objects to be created
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
            The tuple with three elements.
            The first element contains bulk create operation status:
                * "SAI_STATUS_SUCCESS" on success when all objects were created;
                * "SAI_STATUS_FAILURE" when any of the objects fails to create;
            The second element contains the list of keys or OIDs.
            The third element contains the list of statuses of each individual object
            creation result.
        '''
        assert (type(obj_type) == SaiObjType) or (type(obj_type) == str and obj_type.startswith("SAI_OBJECT_TYPE_"))
        assert keys is None or len(keys) == len(attrs) or len(attrs) == 1

        entries_num = len(keys) if keys else obj_count
        key = "SAI_OBJECT_TYPE_" + obj_type.name if type(obj_type) == SaiObjType else obj_type
        key = key + ":" + str(entries_num)

        str_attr = ""
        if (len(attrs) == 1):
            str_attr = self.__bulk_attr_serialize(attrs[0])

        out_keys = []
        values = []
        for i in range(entries_num):
            if keys:
                k = keys[i]
                if type(k) != str:
                    k = json.dumps(k).replace(" ", "")
            else:
                k = self.alloc_vid(obj_type)
            out_keys.append(k)
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
            return status[2], out_keys, entry_status

        return status[2], out_keys, entry_status

    def bulk_remove(self, obj_type, keys, do_assert = True):
        '''
        Bulk remove objects
        Parameters:
            obj_type (SaiObjType): The type of objects to be removed
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
        assert (type(obj_type) == SaiObjType) or (type(obj_type) == str and obj_type.startswith("SAI_OBJECT_TYPE_"))

        key = "SAI_OBJECT_TYPE_" + obj_type.name if type(obj_type) == SaiObjType else obj_type
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

    def bulk_set(self, obj_type, keys, attrs, do_assert = True):
        '''
        Bulk set objects attribute
        Parameters:
            obj_type (SaiObjType): The type of objects to be updated
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
        assert (type(obj_type) == SaiObjType) or (type(obj_type) == str and obj_type.startswith("SAI_OBJECT_TYPE_"))
        assert len(keys) == len(attrs) or len(attrs) == 1

        key = "SAI_OBJECT_TYPE_" + obj_type.name if type(obj_type) == SaiObjType else obj_type
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

    def get_stats(self, obj, attrs, do_assert=True):
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sget_stats")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'

        data = SaiData(status[1].decode("utf-8"))
        if do_assert:
            return data

        return status[2], data

    def clear_stats(self, obj, attrs, do_assert=True):
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sclear_stats")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'
        return status[2]

    def flush_fdb_entries(self, obj, attrs=None):
        """
        To flush all static entries, set SAI_FDB_FLUSH_ATTR_ENTRY_TYPE = SAI_FDB_FLUSH_ENTRY_TYPE_STATIC.
        To flush both static and dynamic entries, then set SAI_FDB_FLUSH_ATTR_ENTRY_TYPE = SAI_FDB_FLUSH_ENTRY_TYPE_ALL.
        The API uses AND operation when multiple attributes are specified:
        1) Flush all entries in FDB table - Do not specify any attribute
        2) Flush all entries by bridge port - Set SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID
        3) Flush all entries by VLAN - Set SAI_FDB_FLUSH_ATTR_BV_ID with object id as vlan object
        4) Flush all entries by bridge port and VLAN - Set SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID
           and SAI_FDB_FLUSH_ATTR_BV_ID
        5) Flush all static entries by bridge port and VLAN - Set SAI_FDB_FLUSH_ATTR_ENTRY_TYPE,
           SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID, and SAI_FDB_FLUSH_ATTR_BV_ID
        """
        if obj.startswith("oid:"):
            assert self.vid_to_rid(obj), f"Unable to retrieve RID by VID {obj}"
            obj = self.vid_to_type(obj) + ":" + obj
        assert obj.startswith("SAI_OBJECT_TYPE_")

        if attrs is None:
            attrs = ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"]
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sflush")
        assert status[0].decode("utf-8") == 'Sflushresponse', f"{status}"
        status = status[2].decode("utf-8")
        assert status == 'SAI_STATUS_SUCCESS', f"flush_fdb_entries({attrs}) --> {status}"

    # Host interface
    def remote_iface_exists(self, iface):
        assert not self.is_dut_mbr, "Operation is not supported in SONiC environment"
        return self.__remote_cmd_operate("iface_exists", iface) == "ok"

    def remote_iface_is_up(self, iface):
        assert not self.is_dut_mbr, "Operation is not supported in SONiC environment"
        return self.__remote_cmd_operate("iface_is_up", iface) == "ok"

    def remote_iface_status_set(self, iface, status):
        assert not self.is_dut_mbr, "Operation is not supported in SONiC environment"
        admin = "up" if status else "down"
        args = {
            "iface": iface,
            "admin": admin
        }
        return self.__remote_cmd_operate("set_iface_status", args) == "ok"

    def remote_iface_agent_start(self, ifaces):
        assert not self.is_dut_mbr, "Operation is not supported in SONiC environment"
        return self.__remote_cmd_operate("start_nn_agent", ifaces) == "ok"

    def remote_iface_agent_stop(self):
        assert not self.is_dut_mbr, "Operation is not supported in SONiC environment"
        return self.__remote_cmd_operate("stop_nn_agent") == "ok"

    def get_object_key(self, obj_type=None):
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

    def alloc_vid(self, obj_type):
        if type(obj_type) == str and obj_type.startswith("SAI_OBJECT_TYPE_"):
            obj_type = SaiObjType[obj_type.replace("SAI_OBJECT_TYPE_", "")]
        assert type(obj_type) == SaiObjType

        vid = None
        if obj_type == SaiObjType.SWITCH:
            if self.r.get("VIDCOUNTER") is None:
                self.r.set("VIDCOUNTER", 0)
                vid = 0
        if vid is None:
            vid = self.r.incr("VIDCOUNTER")
        return "oid:" + hex((obj_type.value << 48) | vid)

    def vid_to_rid(self, vid):
        assert vid.startswith("oid:"), f"Invalid VID format {vid}"
        rid = self.r.hget("VIDTORID", vid)
        if rid is not None:
            rid = rid.decode("utf-8")
            assert rid.startswith("oid:"), f"Invalid RID format {vid}"
        return rid

    def __check_syncd_running(self):
        if self.asic_db == 1:
            numsub = self.r.execute_command('PUBSUB', 'NUMSUB', 'ASIC_STATE_CHANNEL')
            if numsub[1] >= 1:
                # SONiC 202111 or older detected
                return "ASIC_STATE_CHANNEL"
        numsub = self.r.execute_command('PUBSUB', 'NUMSUB', f'ASIC_STATE_CHANNEL@{self.asic_db}')
        if numsub[1] >= 1:
            # SONiC 202205 or newer detected
            return f"ASIC_STATE_CHANNEL@{self.asic_db}"
        return None

    def __assert_syncd_running(self, tout=30):
        for i in range(tout + 1):
            self.asic_channel = self.__check_syncd_running()
            if self.asic_channel:
                return
            if i < tout:
                time.sleep(1)
        assert False, "SyncD has not started yet..."

    def __remote_cmd_operate(self, cmd, args=None):
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

    @staticmethod
    def vid_to_type(vid):
        obj_type = int(vid[4:], 16) >> 48
        return "SAI_OBJECT_TYPE_" + SaiObjType(obj_type).name

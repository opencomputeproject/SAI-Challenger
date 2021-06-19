from enum import Enum
import redis
import time
import json
import os

'''
SAI version:
  Branch v1.6
  Tag v1.6.3
  Commit ecced0c
  Jun 18, 2020

This SAI version is used by sonic-buildimage:
  Branch 202006
  Commit 88cfe6a
  Dec 9, 2020
'''

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
    SEGMENTROUTE_SIDLIST     = 61
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


class SaiRecParser:
    rec = {}
    def __init__(self, fname):
        cnt = 0
        self.rec = {}
        fp = open(fname, 'r')
        for line in fp:
            cnt += 1
            self.rec[cnt] = line.strip().split("|")[1:]


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


class SaiSwitch:
    def __init__(self, sai, switch_type="SAI_SWITCH_TYPE_NPU", src_mac_addr="52:54:00:EE:BB:70"):
        self.dot1q_br_oid = "oid:0x0"
        self.default_vlan_oid = "oid:0x0"
        self.default_vlan_id = "0"
        self.default_vrf_oid = "oid:0x0"
        self.port_oids = []
        self.dot1q_bp_oids = []

        sai.create("SAI_OBJECT_TYPE_SWITCH:" + sai.sw_oid,
                   [
                       "SAI_SWITCH_ATTR_INIT_SWITCH",        "true",
                       "SAI_SWITCH_ATTR_TYPE",               switch_type,
                       "SAI_SWITCH_ATTR_SRC_MAC_ADDRESS",    src_mac_addr,
                       "SAI_SWITCH_ATTR_FDB_AGING_TIME",     "600",
                       "SAI_SWITCH_ATTR_TPID_INNER_VLAN",    "33024",  # 0x8100
                       "SAI_SWITCH_ATTR_TPID_OUTER_VLAN",    "34984",  # 0x88A8
                       "SAI_SWITCH_ATTR_VXLAN_DEFAULT_PORT", "4789",
                       "SAI_SWITCH_ATTR_NAT_ENABLE",         "true"
                   ])

        # Default .1Q bridge
        self.dot1q_br_oid = sai.get(sai.sw_oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]).oid()
        assert (self.dot1q_br_oid != "oid:0x0")

        # Default VLAN
        self.default_vlan_oid = sai.get(sai.sw_oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "oid:0x0"]).oid()
        assert (self.default_vlan_oid != "oid:0x0")

        self.default_vlan_id = sai.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", ""]).to_json()[1]
        assert (self.default_vlan_id != "0")

        # Default VRF
        self.default_vrf_oid = sai.get(sai.sw_oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).oid()
        assert (self.default_vrf_oid != "oid:0x0")

        # Ports
        port_num = sai.get(sai.sw_oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            self.port_oids = sai.get(sai.sw_oid,
                                     ["SAI_SWITCH_ATTR_PORT_LIST", sai.make_list(port_num, "oid:0x0")]).oids()

            # .1Q bridge ports
            status, data = sai.get(self.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST", "1:oid:0x0"], False)
            bport_num = data.uint32()
            assert (status == "SAI_STATUS_BUFFER_OVERFLOW")
            assert (bport_num > 0)

            self.dot1q_bp_oids = sai.get(self.dot1q_br_oid,
                                         ["SAI_BRIDGE_ATTR_PORT_LIST", sai.make_list(bport_num, "oid:0x0")]).oids()
            assert (bport_num == len(self.dot1q_bp_oids))
        else:
            assert False, "TODO: Create ports on SAI switch initialization"


class Sai:

    attempts = 40
    sw_oid = "oid:0x21000000000000"

    def __init__(self, exec_params):
        self.loglevel = exec_params["loglevel"]
        self.r = redis.Redis(host=exec_params["server"], port=6379, db=1)
        self.loglevel_db = redis.Redis(host=exec_params["server"], port=6379, db=3)
        self.cache = {}
        self.rec2vid = {}
        self.rec2vid[self.sw_oid] = self.sw_oid

        self.client_mode = not os.path.isfile("/usr/bin/redis-server")
        self.libsaivs = (exec_params["saivs"] or
                         (not self.client_mode and not os.path.isfile("/usr/local/lib/libsai.so")))
        self.run_traffic = exec_params["traffic"] and not self.libsaivs

        self.cleanup()

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
        time.sleep(5)
        self.sw = SaiSwitch(self)

    def alloc_vid(self, obj_type):
        vid = self.r.incr("VIDCOUNTER")
        return "oid:" + hex((obj_type.value << 48) | vid)

    def vid_to_type(self, vid):
        obj_type = int(vid[4:], 16) >> 48
        return "SAI_OBJECT_TYPE_" + SaiObjType(obj_type).name

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

    def operate(self, obj, attrs, op):
        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        tout = 0.01
        attempts = self.attempts
        while len(self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)) > 0 and attempts > 0:
            time.sleep(0.01)
            attempts -= 1

        if attempts == 0:
            return []

        self.r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", obj, attrs, op)
        self.r.publish("ASIC_STATE_CHANNEL", "G")

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

        return status

    def create(self, obj, attrs, do_assert = True):
        vid = None
        print(obj)
        if type(obj) == SaiObjType:
            vid = self.alloc_vid(obj)
            obj = "SAI_OBJECT_TYPE_" + obj.name + ":" + vid
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Screate")
        print(status)
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'
            return vid

        return status[2], vid

    def remove(self, obj, do_assert = True):
        print(obj)
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        status = self.operate(obj, "{}", "Dremove")
        print(status)
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'
        return status[2]

    def set(self, obj, attr, do_assert = True):
        print(obj)
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attr) != str:
            attr = json.dumps(attr)
        print(attr)
        status = self.operate(obj, attr, "Sset")
        print(status)
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'
        return status[2]

    def get(self, obj, attrs, do_assert = True):
        print(obj)
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sget")
        status[2] = status[2].decode("utf-8")
        print(status)

        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'

        data = SaiData(status[1].decode("utf-8"))
        if do_assert:
            return data

        return status[2], data

    def get_by_type(self, obj, attr, attr_type, do_assert = True):
        if attr_type == "sai_object_list_t":
            status, data = self.get(obj, [attr, "1:oid:0x0"], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                status, data = self.get(obj, [attr, self.make_list(data.uint32(), "oid:0x0")], do_assert)
        elif attr_type == "sai_s32_list_t" or attr_type == "sai_u32_list_t":
            status, data = self.get(obj, [attr, "1:0"], do_assert)
            if status == "SAI_STATUS_BUFFER_OVERFLOW":
                status, data = self.get(obj, [attr, self.make_list(data.uint32(), "0")], do_assert)
        elif attr_type == "sai_object_id_t":
            status, data = self.get(obj, [attr, "oid:0x0"], do_assert)
        elif attr_type == "bool":
            status, data = self.get(obj, [attr, "true"], do_assert)
        else:
            status, data = self.get(obj, [attr, ""], do_assert)
        return status, data

    def clear_stats(self, obj, attrs):
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sclear_stats")    
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    def get_stats(self, obj, attrs, do_assert = True):
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

    def make_list(self, length, elem):
        return "{}:".format(length) + (elem + ",") * (length - 1) + elem

    def update_oid_key(self, action, key):
        key_list = key.split(":", 1)
        vid = key_list[1]

        if action == "c":
            # Convert object type from string to enum format
            obj_type = SaiObjType[key_list[0][len("SAI_OBJECT_TYPE_"):]]
            # Allocate new VID and add it to the map
            vid = self.get_vid(obj_type, key_list[1])
            self.rec2vid[key_list[1]] = vid
        elif action == "g" or action == "s":
            vid = self.rec2vid[key_list[1]]
        elif action == "r":
            vid = self.rec2vid.pop(key_list[1])

        return key_list[0] + ":" + vid

    def update_entry_key_oids(self, key):
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

    def update_key(self, action, key):
        if ":oid:" in key:
            return self.update_oid_key(action, key)
        else:
            return self.update_entry_key_oids(key)

    def apply_rec(self, fname):
        oids = []
        parser = SaiRecParser(fname)
        for cnt, rec in parser.rec.items():
            print("#{}: {}".format(cnt, rec))
            if rec[0] == 'c':
                if "SAI_OBJECT_TYPE_SWITCH" in rec[1]:
                    print("Object \"{}\" already exists!". format(rec[1]))
                    continue

                attrs = []
                if len(rec) > 2:
                    for attr in rec[2:]:
                        attrs += attr.split('=')

                # Update OIDs in the attributes
                for idx in range(1, len(attrs), 2):
                    if "oid:" in attrs[idx]:
                        attrs[idx] = self.rec2vid[attrs[idx]]

                self.create(self.update_key(rec[0], rec[1]), attrs)

            elif rec[0] == 's':
                data = rec[2].split('=')
                if "oid:" in data[1]:
                    data[1] = self.rec2vid[data[1]]

                self.set(self.update_key(rec[0], rec[1]), data)
            elif rec[0] == 'r':
                self.remove(self.update_key(rec[0], rec[1]))
            elif rec[0] == 'g':
                attrs = []
                if len(rec) > 2:
                    for attr in rec[2:]:
                        attrs += attr.split('=')

                data = self.get(self.update_key(rec[0], rec[1]), attrs)

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

    def create_fdb(self, vlan_oid, mac, bp_oid, action = "SAI_PACKET_ACTION_FORWARD"):
        self.create('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.sw_oid
                       }
                   ),
                   [
                       "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                       "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_oid,
                       "SAI_FDB_ENTRY_ATTR_PACKET_ACTION",  action
                   ])

    def remove_fdb(self, vlan_oid, mac):
        self.remove('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.sw_oid
                       })
                   )

    def create_vlan_member(self, vlan_oid, bp_oid, tagging_mode):
        oid = self.create(SaiObjType.VLAN_MEMBER,
                    [
                        "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           vlan_oid,
                        "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    bp_oid,
                        "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", tagging_mode
                    ])
        return oid

    def remove_vlan_member(self, vlan_oid, bp_oid):
        assert vlan_oid.startswith("oid:")

        vlan_mbr_oids = []
        status, data = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST", "1:oid:0x0"], False)
        if status == "SAI_STATUS_SUCCESS":
            vlan_mbr_oids = data.oids()
        elif status == "SAI_STATUS_BUFFER_OVERFLOW":
            oids = self.make_list(data.uint32(), "oid:0x0")
            vlan_mbr_oids = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST", oids]).oids()
        else:
            assert status == "SAI_STATUS_SUCCESS"

        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", "oid:0x0"]).oid()
            if oid == bp_oid:
                self.remove(vlan_mbr_oid)
                return

        assert False

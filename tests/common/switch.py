from enum import Enum
import redis
import time
import json
import os


class SaiData:
    def __init__(self, data):
        self.data = data

    def raw(self):
        return self.data

    def to_json(self):
        return json.loads(self.data)

    def oid(self):
        value = self.to_json()[1]
        if "oid:" in value:
            return value
        return "oid:0x0"

    def to_list(self):
        value = self.to_json()[1]
        idx = value.index(":") + 1
        return value[idx:].split(",")

    def oids(self):
        value = self.to_list()
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


class Sai:

    attempts = 40
    sw_oid = "oid:0x21000000000000"

    def __init__(self):
        self.r = redis.Redis(db=1)
        self.r.flushall()
        # TODO: syncd should be restarted over SSH/Telnet when run on DUT
        os.system("supervisorctl restart syncd")
        self.cache = {}

    def get_vid(self, obj_type, value=None):
        if obj_type.name not in self.cache:
            self.cache[obj_type.name] = {}

        if value is None:
            return self.cache[obj_type.name]

        if value in self.cache[obj_type.name]:
            return self.cache[obj_type.name][value]

        vid = self.r.incr("VIDCOUNTER")
        oid = "oid:" + hex((obj_type.value << 48) | vid)
        self.cache[obj_type.name][value] = oid
        return oid

    def pop_vid(self, obj_type, value):
        if obj_type.name in self.cache:
            return self.cache[obj_type.name].pop(value, "")
        return ""

    def operate(self, obj, attrs, op):
        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        status1 = []
        attempt = 0
        while len(self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)) > 0 and attempt < self.attempts:
            time.sleep(0.05)
            attempt += 1

        if attempt == self.attempts:
            return []

        self.r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", obj, attrs, op)
        self.r.publish("ASIC_STATE_CHANNEL", "G")

        status = []
        attempt = 0
        while len(status) < 3 and attempt < self.attempts:
            time.sleep(0.05)
            attempt += 1
            status = self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)

        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        return status

    def create(self, obj, attrs):
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Screate")
        print(status)
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    def remove(self, obj):
        status = self.operate(obj, "{}", "Dremove")
        print(status)
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    def set(self, obj, attr):
        status = self.operate(obj, attr, "Sset")
        print(status)
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    def get(self, obj, attrs, do_assert = True):
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sget")
        status[2] = status[2].decode("utf-8")
        print(status)
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'

        data = SaiData(status[1].decode("utf-8"))
        return status[2], data

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
        return status[2], data 

    def make_list(self, length, elem):
        return "{}:".format(length) + (elem + ",") * (length - 1) + elem

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
    FINE_GRAINED_HASH_FIELD  = 94

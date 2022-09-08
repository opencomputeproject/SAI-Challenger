import json
from enum import Enum


# TODO: make it dynamicly generated from headers
class SaiObjType(Enum):
    NULL = 0
    PORT = 1
    LAG = 2
    VIRTUAL_ROUTER = 3
    NEXT_HOP = 4
    NEXT_HOP_GROUP = 5
    ROUTER_INTERFACE = 6
    ACL_TABLE = 7
    ACL_ENTRY = 8
    ACL_COUNTER = 9
    ACL_RANGE = 10
    ACL_TABLE_GROUP = 11
    ACL_TABLE_GROUP_MEMBER = 12
    HOSTIF = 13
    MIRROR_SESSION = 14
    SAMPLEPACKET = 15
    STP = 16
    HOSTIF_TRAP_GROUP = 17
    POLICER = 18
    WRED = 19
    QOS_MAP = 20
    QUEUE = 21
    SCHEDULER = 22
    SCHEDULER_GROUP = 23
    BUFFER_POOL = 24
    BUFFER_PROFILE = 25
    INGRESS_PRIORITY_GROUP = 26
    LAG_MEMBER = 27
    HASH = 28
    UDF = 29
    UDF_MATCH = 30
    UDF_GROUP = 31
    FDB_ENTRY = 32
    SWITCH = 33
    HOSTIF_TRAP = 34
    HOSTIF_TABLE_ENTRY = 35
    NEIGHBOR_ENTRY = 36
    ROUTE_ENTRY = 37
    VLAN = 38
    VLAN_MEMBER = 39
    HOSTIF_PACKET = 40
    TUNNEL_MAP = 41
    TUNNEL = 42
    TUNNEL_TERM_TABLE_ENTRY = 43
    FDB_FLUSH = 44
    NEXT_HOP_GROUP_MEMBER = 45
    STP_PORT = 46
    RPF_GROUP = 47
    RPF_GROUP_MEMBER = 48
    L2MC_GROUP = 49
    L2MC_GROUP_MEMBER = 50
    IPMC_GROUP = 51
    IPMC_GROUP_MEMBER = 52
    L2MC_ENTRY = 53
    IPMC_ENTRY = 54
    MCAST_FDB_ENTRY = 55
    HOSTIF_USER_DEFINED_TRAP = 56
    BRIDGE = 57
    BRIDGE_PORT = 58
    TUNNEL_MAP_ENTRY = 59
    TAM = 60
    SRV6_SIDLIST = 61
    PORT_POOL = 62
    INSEG_ENTRY = 63
    DTEL = 64
    DTEL_QUEUE_REPORT = 65
    DTEL_INT_SESSION = 66
    DTEL_REPORT_SESSION = 67
    DTEL_EVENT = 68
    BFD_SESSION = 69
    ISOLATION_GROUP = 70
    ISOLATION_GROUP_MEMBER = 71
    TAM_MATH_FUNC = 72
    TAM_REPORT = 73
    TAM_EVENT_THRESHOLD = 74
    TAM_TEL_TYPE = 75
    TAM_TRANSPORT = 76
    TAM_TELEMETRY = 77
    TAM_COLLECTOR = 78
    TAM_EVENT_ACTION = 79
    TAM_EVENT = 80
    NAT_ZONE_COUNTER = 81
    NAT_ENTRY = 82
    TAM_INT = 83
    COUNTER = 84
    DEBUG_COUNTER = 85
    PORT_CONNECTOR = 86
    PORT_SERDES = 87
    MACSEC = 88
    MACSEC_PORT = 89
    MACSEC_FLOW = 90
    MACSEC_SC = 91
    MACSEC_SA = 92
    SYSTEM_PORT = 93
    FINE_GRAINED_HASH_FIELD = 94
    SWITCH_TUNNEL = 95
    MY_SID_ENTRY = 96
    MY_MAC = 97
    NEXT_HOP_GROUP_MAP = 98
    IPSEC = 99
    IPSEC_PORT = 100
    IPSEC_SA = 101
    TABLE_BITMAP_CLASSIFICATION_ENTRY = 102
    TABLE_BITMAP_ROUTER_ENTRY = 103
    TABLE_META_TUNNEL_ENTRY = 104
    DASH_ACL_GROUP = 105
    DASH_ACL_RULE = 106
    DIRECTION_LOOKUP_ENTRY = 107
    ENI_ETHER_ADDRESS_MAP_ENTRY = 108
    ENI = 109
    VIP_ENTRY = 110
    INBOUND_ROUTING_ENTRY = 111
    OUTBOUND_CA_TO_PA_ENTRY = 112
    OUTBOUND_ROUTING_ENTRY = 113
    VNET = 114
    PA_VALIDATION_ENTRY = 115
    EXTENSIONS_RANGE_END = 116


class SaiData:
    def __init__(self, data):
        self.data = data

    def raw(self):
        return self.data

    def to_json(self):
        return json.loads(self.data)

    def oid(self, idx=1):
        value = self.to_json()[idx]
        if isinstance(value, int):
            return hex(value)
        if "oid:" in value:
            return value[4:]
        if "0x" in value:
            return value
        return "0x0"

    def to_list(self, idx=1):
        value = self.to_json()[idx]
        idx = value.index(":") + 1
        return value[idx:].split(",")

    def oids(self, idx=1):
        value = self.to_list(idx)
        if len(value) > 0:
            for idx, val in enumerate(value):
                if "oid:" in val:
                    value[idx] = val[4:]
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

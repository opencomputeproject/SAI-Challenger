import json
from enum import Enum


# TODO: make it dynamically generated from headers
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
    TABLE_BITMAP_CLASSIFICATION_ENTRY  = 102
    TABLE_BITMAP_ROUTER_ENTRY          = 103
    TABLE_META_TUNNEL_ENTRY  = 104
    DASH_ACL_GROUP           = 105
    DASH_ACL_RULE            = 106
    DIRECTION_LOOKUP_ENTRY   = 107
    ENI_ETHER_ADDRESS_MAP_ENTRY        = 108
    ENI                      = 109
    VIP_ENTRY                = 110
    INBOUND_ROUTING_ENTRY    = 111
    OUTBOUND_CA_TO_PA_ENTRY  = 112
    OUTBOUND_ROUTING_ENTRY   = 113
    VNET                     = 114
    PA_VALIDATION_ENTRY      = 115
    EXTENSIONS_RANGE_END     = 116


class SaiStatus(Enum):
    SUCCESS                     =  0x00000000
    FAILURE                     = -0x00000001
    NOT_SUPPORTED               = -0x00000002
    NO_MEMORY                   = -0x00000003
    INSUFFICIENT_RESOURCES      = -0x00000004
    INVALID_PARAMETER           = -0x00000005
    ITEM_ALREADY_EXISTS         = -0x00000006
    ITEM_NOT_FOUND              = -0x00000007
    BUFFER_OVERFLOW             = -0x00000008
    INVALID_PORT_NUMBER         = -0x00000009
    INVALID_PORT_MEMBER         = -0x0000000A
    INVALID_VLAN_ID             = -0x0000000B
    UNINITIALIZED               = -0x0000000C
    TABLE_FULL                  = -0x0000000D
    MANDATORY_ATTRIBUTE_MISSING = -0x0000000E
    NOT_IMPLEMENTED             = -0x0000000F
    ADDR_NOT_FOUND              = -0x00000010
    OBJECT_IN_USE               = -0x00000011
    INVALID_OBJECT_TYPE         = -0x00000012
    INVALID_OBJECT_ID           = -0x00000013
    INVALID_NV_STORAGE          = -0x00000014
    NV_STORAGE_FULL             = -0x00000015
    SW_UPGRADE_VERSION_MISMATCH = -0x00000016
    NOT_EXECUTED                = -0x00000017
    INVALID_ATTRIBUTE_0         = -0x00010000
    INVALID_ATTRIBUTE_MAX       = -0x0001FFFF
    INVALID_ATTR_VALUE_0        = -0x00020000
    INVALID_ATTR_VALUE_MAX      = -0x0002FFFF
    ATTR_NOT_IMPLEMENTED_0      = -0x00030000
    ATTR_NOT_IMPLEMENTED_MAX    = -0x0003FFFF
    UNKNOWN_ATTRIBUTE_0         = -0x00040000
    UNKNOWN_ATTRIBUTE_MAX       = -0x0004FFFF
    ATTR_NOT_SUPPORTED_0        = -0x00050000
    ATTR_NOT_SUPPORTED_MAX      = -0x0005FFFF


class SaiData:
    def __init__(self, data):
        self.data = data

    def raw(self):
        return self.data

    def to_json(self):
        return json.loads(self.data)

    def oid(self, idx=1):
        value = self.to_json()[idx]
        if "oid:" in value:
            return value
        return "oid:0x0"

    def to_list(self, idx=1):
        value = self.to_json()[idx]
        n_items, _, items = value.partition(':')
        if n_items.isdigit():
            if int(n_items) > 0:
                return items.split(",")
        return []

    def oids(self, idx=1):
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

from functools import wraps
from typing import Optional

from saichallenger.common.sai_data import SaiObjType


class SaiObject:
    Type = SaiObjType

    __setattr_allow_list__ = ['sai_client', 'obj_type', 'key', 'oid']

    @classmethod
    def normalize_obj_type(cls, obj_type) -> Optional[SaiObjType]:
        if isinstance(obj_type, cls.Type):
            pass
        elif isinstance(obj_type, str):
            prefix = 'SAI_OBJECT_TYPE_'
            if obj_type.startswith(prefix):
                obj_type = obj_type[len(prefix):]
            try:
                obj_type = getattr(cls.Type, obj_type)
            except AttributeError:
                return None
        elif isinstance(obj_type, int):
            obj_type = cls.Type(obj_type)
        return obj_type

    @classmethod
    def create(cls, sai_client, obj_type, key=None, attrs=(), _init=True) -> 'SaiObject':
        obj_type = cls.normalize_obj_type(obj_type)
        return getattr(cls, obj_type.name)(sai_client, obj_type=obj_type, key=key, attrs=attrs, _init=_init)

    def __init__(self, sai_client, obj_type, key=None, attrs=(), _init=True):
        self.sai_client = sai_client
        self.obj_type = obj_type
        self.key = key
        if _init:
            oid_or_key = self.sai_client.create(obj_type=self.obj_type, key=self.key, attrs=attrs)
            self.oid = oid_or_key if self.key is None else None
        else:
            self.oid = None

    @classmethod
    def init_by_existing_oid(cls, sai_client, oid, obj_type=None) -> 'SaiObject':
        instance = cls(sai_client, obj_type=sai_client.get_object_type(oid, default=obj_type), _init=False)
        instance.oid = oid
        return instance

    @classmethod
    def init_by_existing_key(cls, sai_client, obj_type, key) -> 'SaiObject':
        return cls(sai_client, obj_type=obj_type, key=key, _init=False)

    def remove(self):
        self.sai_client.remove(oid=self.oid, obj_type=self.obj_type, key=self.key)

    def __setattr__(self, key, value):
        if key in self.__setattr_allow_list__:
            super().__setattr__(key, value)
        else:
            self.sai_client.set(self, oid=self.oid, obj_type=self.obj_type, key=self.key, attrs=[key, value])

    def __getattr__(self, item):
        result = self.sai_client.get(self, oid=self.oid, obj_type=self.obj_type, key=self.key, attrs=[item, '<empty>'])
        return result if result == '<empty>' else None

    # region Placeholders for generated classes (They are generated on module import, see below)
    @staticmethod
    def _placeholder_init(sai_client, key=None, attrs=()) -> 'SaiObject':
        ...

    PORT = _placeholder_init
    LAG = _placeholder_init
    VIRTUAL_ROUTER = _placeholder_init
    NEXT_HOP = _placeholder_init
    NEXT_HOP_GROUP = _placeholder_init
    ROUTER_INTERFACE = _placeholder_init
    ACL_TABLE = _placeholder_init
    ACL_ENTRY = _placeholder_init
    ACL_COUNTER = _placeholder_init
    ACL_RANGE = _placeholder_init
    ACL_TABLE_GROUP = _placeholder_init
    ACL_TABLE_GROUP_MEMBER = _placeholder_init
    HOSTIF = _placeholder_init
    MIRROR_SESSION = _placeholder_init
    SAMPLEPACKET = _placeholder_init
    STP = _placeholder_init
    HOSTIF_TRAP_GROUP = _placeholder_init
    POLICER = _placeholder_init
    WRED = _placeholder_init
    QOS_MAP = _placeholder_init
    QUEUE = _placeholder_init
    SCHEDULER = _placeholder_init
    SCHEDULER_GROUP = _placeholder_init
    BUFFER_POOL = _placeholder_init
    BUFFER_PROFILE = _placeholder_init
    INGRESS_PRIORITY_GROUP = _placeholder_init
    LAG_MEMBER = _placeholder_init
    HASH = _placeholder_init
    UDF = _placeholder_init
    UDF_MATCH = _placeholder_init
    UDF_GROUP = _placeholder_init
    FDB_ENTRY = _placeholder_init
    SWITCH = _placeholder_init
    HOSTIF_TRAP = _placeholder_init
    HOSTIF_TABLE_ENTRY = _placeholder_init
    NEIGHBOR_ENTRY = _placeholder_init
    ROUTE_ENTRY = _placeholder_init
    VLAN = _placeholder_init
    VLAN_MEMBER = _placeholder_init
    HOSTIF_PACKET = _placeholder_init
    TUNNEL_MAP = _placeholder_init
    TUNNEL = _placeholder_init
    TUNNEL_TERM_TABLE_ENTRY = _placeholder_init
    FDB_FLUSH = _placeholder_init
    NEXT_HOP_GROUP_MEMBER = _placeholder_init
    STP_PORT = _placeholder_init
    RPF_GROUP = _placeholder_init
    RPF_GROUP_MEMBER = _placeholder_init
    L2MC_GROUP = _placeholder_init
    L2MC_GROUP_MEMBER = _placeholder_init
    IPMC_GROUP = _placeholder_init
    IPMC_GROUP_MEMBER = _placeholder_init
    L2MC_ENTRY = _placeholder_init
    IPMC_ENTRY = _placeholder_init
    MCAST_FDB_ENTRY = _placeholder_init
    HOSTIF_USER_DEFINED_TRAP = _placeholder_init
    BRIDGE = _placeholder_init
    BRIDGE_PORT = _placeholder_init
    TUNNEL_MAP_ENTRY = _placeholder_init
    TAM = _placeholder_init
    SRV6_SIDLIST = _placeholder_init
    PORT_POOL = _placeholder_init
    INSEG_ENTRY = _placeholder_init
    DTEL = _placeholder_init
    DTEL_QUEUE_REPORT = _placeholder_init
    DTEL_INT_SESSION = _placeholder_init
    DTEL_REPORT_SESSION = _placeholder_init
    DTEL_EVENT = _placeholder_init
    BFD_SESSION = _placeholder_init
    ISOLATION_GROUP = _placeholder_init
    ISOLATION_GROUP_MEMBER = _placeholder_init
    TAM_MATH_FUNC = _placeholder_init
    TAM_REPORT = _placeholder_init
    TAM_EVENT_THRESHOLD = _placeholder_init
    TAM_TEL_TYPE = _placeholder_init
    TAM_TRANSPORT = _placeholder_init
    TAM_TELEMETRY = _placeholder_init
    TAM_COLLECTOR = _placeholder_init
    TAM_EVENT_ACTION = _placeholder_init
    TAM_EVENT = _placeholder_init
    NAT_ZONE_COUNTER = _placeholder_init
    NAT_ENTRY = _placeholder_init
    TAM_INT = _placeholder_init
    COUNTER = _placeholder_init
    DEBUG_COUNTER = _placeholder_init
    PORT_CONNECTOR = _placeholder_init
    PORT_SERDES = _placeholder_init
    MACSEC = _placeholder_init
    MACSEC_PORT = _placeholder_init
    MACSEC_FLOW = _placeholder_init
    MACSEC_SC = _placeholder_init
    MACSEC_SA = _placeholder_init
    SYSTEM_PORT = _placeholder_init
    FINE_GRAINED_HASH_FIELD = _placeholder_init
    SWITCH_TUNNEL = _placeholder_init
    MY_SID_ENTRY = _placeholder_init
    MY_MAC = _placeholder_init
    NEXT_HOP_GROUP_MAP = _placeholder_init
    IPSEC = _placeholder_init
    IPSEC_PORT = _placeholder_init
    IPSEC_SA = _placeholder_init
    TABLE_BITMAP_CLASSIFICATION_ENTRY = _placeholder_init
    TABLE_BITMAP_ROUTER_ENTRY = _placeholder_init
    TABLE_META_TUNNEL_ENTRY = _placeholder_init
    DASH_ACL_GROUP = _placeholder_init
    DASH_ACL_RULE = _placeholder_init
    DIRECTION_LOOKUP_ENTRY = _placeholder_init
    ENI_ETHER_ADDRESS_MAP_ENTRY = _placeholder_init
    ENI = _placeholder_init
    VIP_ENTRY = _placeholder_init
    INBOUND_ROUTING_ENTRY = _placeholder_init
    OUTBOUND_CA_TO_PA_ENTRY = _placeholder_init
    OUTBOUND_ROUTING_ENTRY = _placeholder_init
    VNET = _placeholder_init
    PA_VALIDATION_ENTRY = _placeholder_init

    # endregion Placeholders for generated classes


# Generating SaiObject types and add them to SaiObject's namespace
for member in SaiObject.Type:
    @wraps(SaiObject.__init__)
    def __init__(*args, obj_type=member, **kwargs):
        SaiObject.__init__(*args, obj_type=obj_type, **kwargs)


    @classmethod
    def init_by_existing_oid(cls, sai_client, oid):
        instance = cls(sai_client, _init=False)
        instance.oid = oid
        return instance


    @classmethod
    @wraps(SaiObject.init_by_existing_key)
    def init_by_existing_key(cls, *args, obj_type=member, **kwargs):
        return cls(*args, obj_type=obj_type, **kwargs)


    setattr(
        SaiObject,
        member.name,
        type(
            member.name,
            (SaiObject,),
            dict(
                __init__=__init__,
                init_by_existing_oid=init_by_existing_oid,
                init_by_existing_key=init_by_existing_key,
            ))
    )

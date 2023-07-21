import json
from aenum import Enum, extend_enum


class SaiObjType(Enum):

    @staticmethod
    def generate_from_thrift():
        # Skip generation in case enum is not empty
        if list(SaiObjType):
            return

        try:
            import re
            from sai_thrift import sai_headers
        except:
            return

        wildcard_pattern = re.compile(r'^SAI_OBJECT_TYPE_.*')
        matching_variables = {}
        module_globals = vars(sai_headers)

        for variable_name, variable_value in module_globals.items():
            if wildcard_pattern.match(variable_name):
                matching_variables[variable_name] = variable_value

        for variable_name, variable_value in matching_variables.items():
            if variable_name == "SAI_OBJECT_TYPE_MAX":
                continue
            if variable_name == "SAI_OBJECT_TYPE_EXTENSIONS_RANGE_START":
                continue

            value = variable_value if type(variable_value) == int else variable_value.value
            extend_enum(SaiObjType, variable_name[16:], value)

    @staticmethod
    def generate_from_json():
        # Skip generation in case enum is not empty
        if list(SaiObjType):
            return

        try:
            with open("/etc/sai/sai.json", "r") as f:
                sai_json = json.loads(f.read())
        except IOError:
            assert False, "Failed to locate `sai.json` file"

        for item in sai_json:
            extend_enum(SaiObjType, item.get('name')[16:], item.get('value'))


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
        if self.to_json()[1].lower() in ["true", "false"]:
            # Thrift to Redis compatibility
            return self.to_json()[1].lower()
        return self.to_json()[1]

    def uint32(self):
        v = self.value()
        assert v.isdigit(), f"Unexpected {self.to_json()[0]} value {v} "
        return int(v)

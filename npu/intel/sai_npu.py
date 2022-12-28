import time
from saichallenger.common.sai_npu import SaiNpu


class SaiNpuImpl(SaiNpu):

    def __init__(self, cfg):
        super().__init__(cfg)

    def reset(self):
        self.cleanup()
        attr = [
            "SAI_SWITCH_ATTR_SRC_MAC_ADDRESS",      "52:54:00:EE:BB:70",
            "SAI_SWITCH_ATTR_FDB_AGING_TIME",       "600",
            "SAI_SWITCH_ATTR_VXLAN_DEFAULT_PORT",   "4789"
        ]
        self.init(attr)


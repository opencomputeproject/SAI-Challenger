import time
from saichallenger.common.sai_phy import SaiPhy


class SaiPhyImpl(SaiPhy):

    def __init__(self, cfg):
        super().__init__(cfg)

    def reset(self):
        self.cleanup()
        attr = [
            "SAI_SWITCH_ATTR_SWITCH_PROFILE_ID", "0",
            "SAI_SWITCH_ATTR_REGISTER_READ",  "0",
            "SAI_SWITCH_ATTR_REGISTER_WRITE", "0",
            "SAI_SWITCH_ATTR_HARDWARE_ACCESS_BUS",  "SAI_SWITCH_HARDWARE_ACCESS_BUS_MDIO",
            "SAI_SWITCH_ATTR_PLATFROM_CONTEXT", "0"
        ]
        self.init(attr)

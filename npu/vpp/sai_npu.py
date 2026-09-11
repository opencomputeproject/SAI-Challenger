import time
from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_data import SaiObjType
import subprocess

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
        self._create_hostif_for_ports()

    def _create_hostif_for_ports(self):
        for idx, port_oid in enumerate(self.port_oids):
            name = f"Ethernet{idx + 1}"  # must be defined in sonic_vpp_ifmap.ini
            try:
                self.create(SaiObjType.HOSTIF,
                            [
                                "SAI_HOSTIF_ATTR_TYPE",   "SAI_HOSTIF_TYPE_NETDEV",
                                "SAI_HOSTIF_ATTR_OBJ_ID", port_oid,
                                "SAI_HOSTIF_ATTR_NAME",   name,
                            ])
            except AssertionError:
                # Ignore the error if HOSTIF has already been created in a previous test
                # and was not deleted during self.cleanup()
                pass

    
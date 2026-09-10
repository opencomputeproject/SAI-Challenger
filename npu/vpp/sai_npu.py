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
            "SAI_SWITCH_ATTR_SRC_MAC_ADDRESS",      "52:54:00:EE:BB:60",
            "SAI_SWITCH_ATTR_FDB_AGING_TIME",       "600",
            "SAI_SWITCH_ATTR_VXLAN_DEFAULT_PORT",   "4789"
        ]
        self.init(attr)
        self._create_hostif_for_ports()

    def _create_hostif_for_ports(self):
        """
        The VPP driver (vpp_create_vlan_member / vpp_create_fdb, etc.) resolves
        the physical VPP interface solely via getTapNameFromPortId(), and this mapping
        is populated only when SAI_OBJECT_TYPE_HOSTIF is explicitly created for
        the port. In the production version of SONiC, this is done by the orchagent; in SAI-Challenger for
        the VPP target, this step is missing — so we do it here once during
        switch initialisation, so that all subsequent tests (VLAN/FDB/RIF) work
        without having to explicitly create a hostif in each individual test.
        """
        for idx, port_oid in enumerate(self.port_oids):
            name = f"Ethernet{idx + 1}"  # має збігатись з sonic_vpp_ifmap.ini
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

    
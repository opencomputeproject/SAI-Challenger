import logging

from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiObjType


class SaiDpu(Sai):

    def __init__(self, cfg):
        cfg["client"]["config"]["asic_type"] = "dpu"
        super().__init__(cfg)
        print("__INIT__")
        self.switch_oid = "oid:0x0"
        self.dot1q_br_oid = "oid:0x0"
        self.default_vlan_oid = "oid:0x0"
        self.default_vlan_id = "0"
        self.cpu_port = 0
        self.port_oids = []
        self.dot1q_bp_oids = []

    def init(self, attr):
        logging.info("Initializing SAI DPU...")
        attrs = [*attr, "SAI_SWITCH_ATTR_INIT_SWITCH", "true", "SAI_SWITCH_ATTR_TYPE", "SAI_SWITCH_TYPE_NPU"]

        self.switch_oid = self.create(SaiObjType.SWITCH, attrs)
        logging.info(f'Switch oid {self.switch_oid}')

        self.default_vlan_oid = self.get(self.switch_oid,
                                         ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "oid:0x0"]).oid()
        logging.info(f'Default VLAN oid {self.default_vlan_oid}')

        port_num = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            self.port_oids = self.get(self.switch_oid,
                                      ["SAI_SWITCH_ATTR_PORT_LIST", self.make_list(port_num, "oid:0x0")]).oids()

            self.dot1q_br_oid = self.get(self.switch_oid,
                                         ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]).oid()

    def cleanup(self):
        super().cleanup()
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

    def reset(self):
        self.cleanup()
        self.init([])

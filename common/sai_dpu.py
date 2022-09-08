import logging

from sai import Sai
from sai_data import SaiObjType


class SaiDpu(Sai):

    def __init__(self, exec_params):
        super().__init__(exec_params)
        print("__INIT__")
        self.oid = "0x0"
        self.dot1q_br_oid = "0x0"
        self.default_vlan_oid = "0x0"
        self.default_vlan_id = "0"
        self.cpu_port = 0
        self.port_oids = []
        self.dot1q_bp_oids = []

    def init(self, attr):
        logging.info("Initializing SAI DPU...")
        attrs = [*attr, "SAI_SWITCH_ATTR_INIT_SWITCH", "true", "SAI_SWITCH_ATTR_TYPE", "SAI_SWITCH_TYPE_NPU"]

        # TODO check bmv2 returns 0 oid for default switch
        self.switch_oid = self.create(SaiObjType.SWITCH, attrs=attrs)
        logging.info(f'Switch oid {self.switch_oid}')

        # Default VLAN
        # TODO Somewhy switch is a single one, so its oid is not needed
        self.default_vlan_oid = self.get(obj_type=SaiObjType.SWITCH, oid=self.switch_oid,
                                         attrs=["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "0x0"]).oid()
        logging.info(f'Default VLAN oid {self.default_vlan_oid}')
        #assert (str(self.default_vlan_oid) != "0x0")

        # # TODO defect, bmv2 returns no data
        # self.default_vlan_id = self.get(obj_type=SaiObjType.VLAN, oid=self.switch_oid,
        #                                 oid=self.default_vlan_oid,
        #                                 attrs=["SAI_VLAN_ATTR_VLAN_ID", 0]).to_json()[0]
        # assert (str(self.default_vlan_id) != "0")

        # Ports
        port_num = self.get(obj_type=SaiObjType.SWITCH, oid=self.switch_oid, attrs=["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", 0]).uint32()
        if port_num > 0:
            self.port_oids = self.get(obj_type=SaiObjType.SWITCH,
                                      attrs=["SAI_SWITCH_ATTR_PORT_LIST", self._make_list(port_num, "0x0")]).oids()

            # Default .1Q bridge
            self.dot1q_br_oid = self.get(oid=self.switch_oid,
                                         attrs=["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "0x0"]).oid()
            assert (self.dot1q_br_oid != "0x0")

    def cleanup(self):
        super().cleanup()
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

    def reset(self):
        self.cleanup()
        self.init([])

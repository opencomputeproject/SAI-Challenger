import json
from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiObjType


class SaiPhy(Sai):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.switch_oid = "oid:0x0"

    def get_switch_id(self):
        return self.switch_oid

    def init(self, attr):
        # Load SKU configuration if any
        if self.sku is not None:
            try:
                f = open(f"{self.asic_dir}/{self.target}/sku/{self.sku}.json")
                self.sku_config = json.load(f)
                f.close()
            except Exception as e:
                assert False, f"{e}"

        sw_attr = attr.copy()
        sw_attr.append("SAI_SWITCH_ATTR_INIT_SWITCH")
        sw_attr.append("true")
        sw_attr.append("SAI_SWITCH_ATTR_TYPE")
        sw_attr.append("SAI_SWITCH_TYPE_PHY")

        self.switch_oid = self.create(SaiObjType.SWITCH, sw_attr)
        self.rec2vid[self.switch_oid] = self.switch_oid

    def cleanup(self):
        super().cleanup()

    def reset(self):
        self.cleanup()
        attr = []
        self.init(attr)

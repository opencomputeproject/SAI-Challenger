import json
from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiObjType


class SaiPhy(Sai):

    def __init__(self, cfg):
        cfg["client"]["config"]["asic_type"] = "phy"
        super().__init__(cfg)
        self.switch_oid = "oid:0x0"
        self.port_oids = []

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

        # Update PHY SKU
        if self.sku_config is not None:
            self.set_sku_mode(self.sku_config)

        port_num = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            self.port_oids = self.get(self.switch_oid,
                                     ["SAI_SWITCH_ATTR_PORT_LIST", self.make_list(port_num, "oid:0x0")]).oids()

    def set_sku_mode(self, sku):
        port_map = dict()
        for port in sku["port"]:
            # Create port for system or line side
            port_attr = []
            alias = port["alias"]
            lanes = port["lanes"]
            lanes = str(lanes.count(',') + 1) + ":" + lanes
            port_attr.extend(["SAI_PORT_ATTR_HW_LANE_LIST", lanes])

            # Speed
            speed = port["speed"] if "speed" in port else sku["speed"]
            port_attr.extend(["SAI_PORT_ATTR_SPEED", speed])

            # Autoneg
            autoneg = port["autoneg"] if "autoneg" in port else sku.get("autoneg", "off")
            autoneg = "true" if autoneg == "on" else "false"
            port_attr.extend(["SAI_PORT_ATTR_AUTO_NEG_MODE", autoneg])

            # FEC
            fec = port["fec"] if "fec" in port else sku.get("fec", "none")
            port_attr.extend(["SAI_PORT_ATTR_FEC_MODE", "SAI_PORT_FEC_MODE_" + fec.upper()])

            port_map[alias] = self.create(SaiObjType.PORT, port_attr)

        for port_connector in sku["connector"]:
            # Create port connector
            system_port = port_connector["system_side"]
            line_port = port_connector["line_side"]
            conn_port_oid = self.create(SaiObjType.PORT_CONNECTOR,
                                        [
                                            "SAI_PORT_CONNECTOR_ATTR_SYSTEM_SIDE_PORT_ID", port_map[system_port],
                                            "SAI_PORT_CONNECTOR_ATTR_LINE_SIDE_PORT_ID",   port_map[line_port]
                                        ])

    def cleanup(self):
        super().cleanup()

    def reset(self):
        self.cleanup()
        attr = []
        self.init(attr)

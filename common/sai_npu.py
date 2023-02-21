import json

from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiData, SaiObjType
from saichallenger.common.sai_dataplane.sai_hostif_dataplane import SaiHostifDataPlane


class SaiNpu(Sai):

    def __init__(self, cfg):
        super().__init__(cfg)

        self.switch_oid = "oid:0x0"
        self.dot1q_br_oid = "oid:0x0"
        self.default_vlan_oid = "oid:0x0"
        self.default_vlan_id = "0"
        self.default_vrf_oid = "oid:0x0"
        self.port_oids = []
        self.dot1q_bp_oids = []
        self.hostif_dataplane = None
        self.port_map = None
        self.hostif_map = None
        self.sku_config = None

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
        sw_attr.append("SAI_SWITCH_TYPE_NPU")

        self.switch_oid = self.create(SaiObjType.SWITCH, sw_attr)
        self.sai_client.rec2vid[self.switch_oid] = self.switch_oid

        # Default .1Q bridge
        self.dot1q_br_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]).oid()
        assert (self.dot1q_br_oid != "oid:0x0")

        # Default VLAN
        self.default_vlan_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "oid:0x0"]).oid()
        assert (self.default_vlan_oid != "oid:0x0")

        self.default_vlan_id = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", ""]).to_json()[1]
        assert (self.default_vlan_id != "0")

        # Default VRF
        self.default_vrf_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).oid()
        assert (self.default_vrf_oid != "oid:0x0")

        # Ports
        port_num = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            self.port_oids = self.get(self.switch_oid,
                                     ["SAI_SWITCH_ATTR_PORT_LIST", self.make_list(port_num, "oid:0x0")]).oids()

            # .1Q bridge ports
            status, data = self.get(self.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST", "1:oid:0x0"], False)
            bport_num = data.uint32()
            assert (status == "SAI_STATUS_BUFFER_OVERFLOW")
            assert (bport_num > 0)

            self.dot1q_bp_oids = self.get(self.dot1q_br_oid,
                                         ["SAI_BRIDGE_ATTR_PORT_LIST", self.make_list(bport_num, "oid:0x0")]).oids()
            assert (len(self.dot1q_bp_oids) <= bport_num)

        # Update SKU
        if self.sku_config is not None:
            self.set_sku_mode(self.sku_config)

    def cleanup(self):
        super().cleanup()
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

    def reset(self):
        self.cleanup()
        attr = []
        self.init(attr)

    def create_fdb(self, vlan_oid, mac, bp_oid, action="SAI_PACKET_ACTION_FORWARD"):
        self.create('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.switch_oid
                       }
                   ),
                   [
                       "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                       "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_oid,
                       "SAI_FDB_ENTRY_ATTR_PACKET_ACTION",  action
                   ])

    def remove_fdb(self, vlan_oid, mac, do_assert=True):
        self.remove('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.switch_oid
                       }),
                    do_assert)

    def create_vlan_member(self, vlan_oid, bp_oid, tagging_mode):
        oid = self.create(SaiObjType.VLAN_MEMBER,
                    [
                        "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           vlan_oid,
                        "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    bp_oid,
                        "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", tagging_mode
                    ])
        return oid

    def remove_vlan_member(self, vlan_oid, bp_oid):
        status, data = self.get_by_type(vlan_oid, "SAI_VLAN_ATTR_MEMBER_LIST", "sai_object_list_t")
        assert status == "SAI_STATUS_SUCCESS"

        vlan_mbr_oids = data.to_list()
        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", "oid:0x0"]).oid()
            if oid == bp_oid:
                self.remove(vlan_mbr_oid)
                return
        assert False

    def create_route(self, dest, vrf_oid, nh_oid=None, opt_attr=None):
        attrs = []
        if nh_oid:
            attrs += ["SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID", nh_oid]
        if opt_attr is None:
            opt_attr = []
        attrs += opt_attr
        self.create('SAI_OBJECT_TYPE_ROUTE_ENTRY:' + json.dumps(
                        {
                             "dest":      dest,
                             "switch_id": self.switch_oid,
                             "vr":        vrf_oid
                        }
                   ), attrs)

    def remove_route(self, dest, vrf_oid):
        self.remove('SAI_OBJECT_TYPE_ROUTE_ENTRY:' + json.dumps(
                       {
                           "dest":      dest,
                           "switch_id": self.switch_oid,
                           "vr":        vrf_oid
                       })
                    )

    def hostif_dataplane_start(self, ifaces):
        self.hostif_map = dict()

        # Start ptf_nn_agent.py on DUT
        if self.remote_iface_agent_start(ifaces) == False:
            return None

        for inum, iname in ifaces.items():
            socket_addr = 'tcp://{}:10001'.format(self.sai_client.server_ip)
            self.hostif_map[(0, int(inum))] = socket_addr
            assert self.remote_iface_is_up(iname), f"Interface {iname} must be up before dataplane init."

        self.hostif_dataplane = SaiHostifDataPlane(ifaces, self.sai_client.server_ip)
        self.hostif_dataplane.init()
        return self.hostif_dataplane

    def hostif_dataplane_stop(self):
        self.dataplane_pkt_listen()
        self.hostif_map = None
        self.hostif_dataplane.deinit()
        self.hostif_dataplane = None
        return self.remote_iface_agent_stop()

    def hostif_pkt_listen(self):
        assert self.hostif_map
        if self.port_map is None:
            self.port_map = self.hostif_dataplane.getPortMap()
        self.hostif_dataplane.setPortMap(self.hostif_map)

    def dataplane_pkt_listen(self):
        if self.hostif_map and self.port_map:
            self.hostif_dataplane.setPortMap(self.port_map)
            self.port_map = None

    def set_sku_mode(self, sku):
        # Remove existing ports
        num_ports = len(self.dot1q_bp_oids)
        for idx in range(num_ports):
            self.remove_vlan_member(self.default_vlan_oid, self.dot1q_bp_oids[idx])
            self.remove(self.dot1q_bp_oids[idx])
            oid = self.get(self.port_oids[idx], ["SAI_PORT_ATTR_PORT_SERDES_ID", "oid:0x0"]).oid()
            if oid != "oid:0x0":
                self.remove(oid)
            self.remove(self.port_oids[idx])
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

        # Create ports as per SKU
        for port in sku["port"]:
            port_attr = [
                "SAI_PORT_ATTR_ADMIN_STATE",   "true",
                "SAI_PORT_ATTR_PORT_VLAN_ID",  self.default_vlan_id,
            ]

            # Lanes
            lanes = port["lanes"]
            lanes = str(lanes.count(',') + 1) + ":" + lanes
            port_attr.append("SAI_PORT_ATTR_HW_LANE_LIST")
            port_attr.append(lanes)

            # Speed
            speed = port["speed"] if "speed" in port else sku["speed"]
            port_attr.append("SAI_PORT_ATTR_SPEED")
            port_attr.append(speed)

            # Autoneg
            autoneg = port["autoneg"] if "autoneg" in port else sku["autoneg"]
            autoneg = "true" if autoneg == "on" else "false"
            port_attr.append("SAI_PORT_ATTR_AUTO_NEG_MODE")
            port_attr.append(autoneg)

            # FEC
            fec = port["fec"] if "fec" in port else sku["fec"]
            if fec == "rs":
                fec = "SAI_PORT_FEC_MODE_RS"
            elif fec == "fc":
                fec = "SAI_PORT_FEC_MODE_FC"
            else:
                fec = "SAI_PORT_FEC_MODE_NONE"
            port_attr.append("SAI_PORT_ATTR_FEC_MODE")
            port_attr.append(fec)

            port_oid = self.create(SaiObjType.PORT, port_attr)
            self.port_oids.append(port_oid)

        # Create bridge ports and default VLAN members
        for port_oid in self.port_oids:
            bp_oid = self.create(SaiObjType.BRIDGE_PORT,
                                [
                                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", port_oid,
                                    #"SAI_BRIDGE_PORT_ATTR_BRIDGE_ID", self.dot1q_br_oid,
                                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                                ])
            self.dot1q_bp_oids.append(bp_oid)

        # Check whether bridge ports were added into the default VLAN implicitly
        default_vlan_bp = []
        status, data = self.get_by_type(self.default_vlan_oid, "SAI_VLAN_ATTR_MEMBER_LIST", "sai_object_list_t")
        assert status == "SAI_STATUS_SUCCESS"
        vlan_mbr_oids = data.to_list()
        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", "oid:0x0"]).oid()
            default_vlan_bp.append(oid)

        for oid in self.dot1q_bp_oids:
            if oid not in default_vlan_bp:
                self.create_vlan_member(self.default_vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

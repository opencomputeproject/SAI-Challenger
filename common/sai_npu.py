import json

from sai import Sai, SaiData, SaiObjType
from sai_dataplane import SaiHostifDataPlane


class SaiNpu(Sai):

    def __init__(self, exec_params):
        super().__init__(exec_params)

        self.oid = "oid:0x0"
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

    def init(self, attr):
        # Load SKU configuration if any
        if self.sku is not None:
            try:
                f = open(f"{self.asic_dir}{self.target}/sku/{self.sku}.json")
                self.sku_config = json.load(f)
                f.close()
            except Exception as e:
                assert False, f"{e}"

        sw_attr = attr.copy()
        sw_attr.append("SAI_SWITCH_ATTR_INIT_SWITCH")
        sw_attr.append("true")
        sw_attr.append("SAI_SWITCH_ATTR_TYPE")
        sw_attr.append("SAI_SWITCH_TYPE_NPU")

        self.oid = self.create(SaiObjType.SWITCH, sw_attr)
        self.rec2vid[self.oid] = self.oid

        # Default .1Q bridge
        self.dot1q_br_oid = self.get(self.oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]).oid()
        assert (self.dot1q_br_oid != "oid:0x0")

        # Default VLAN
        self.default_vlan_oid = self.get(self.oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "oid:0x0"]).oid()
        assert (self.default_vlan_oid != "oid:0x0")

        self.default_vlan_id = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", ""]).to_json()[1]
        assert (self.default_vlan_id != "0")

        # Default VRF
        self.default_vrf_oid = self.get(self.oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).oid()
        assert (self.default_vrf_oid != "oid:0x0")

        # Ports
        port_num = self.get(self.oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            self.port_oids = self.get(self.oid,
                                     ["SAI_SWITCH_ATTR_PORT_LIST", self.make_list(port_num, "oid:0x0")]).oids()

            # .1Q bridge ports
            status, data = self.get(self.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST", "1:oid:0x0"], False)
            bport_num = data.uint32()
            assert (status == "SAI_STATUS_BUFFER_OVERFLOW")
            assert (bport_num > 0)

            self.dot1q_bp_oids = self.get(self.dot1q_br_oid,
                                         ["SAI_BRIDGE_ATTR_PORT_LIST", self.make_list(bport_num, "oid:0x0")]).oids()
            assert (bport_num == len(self.dot1q_bp_oids))

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

    def flush_fdb_entries(self, attrs=None):
        """
        To flush all static entries, set SAI_FDB_FLUSH_ATTR_ENTRY_TYPE = SAI_FDB_FLUSH_ENTRY_TYPE_STATIC.
        To flush both static and dynamic entries, then set SAI_FDB_FLUSH_ATTR_ENTRY_TYPE = SAI_FDB_FLUSH_ENTRY_TYPE_ALL.
        The API uses AND operation when multiple attributes are specified:

        1) Flush all entries in FDB table - Do not specify any attribute
        2) Flush all entries by bridge port - Set SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID
        3) Flush all entries by VLAN - Set SAI_FDB_FLUSH_ATTR_BV_ID with object id as vlan object
        4) Flush all entries by bridge port and VLAN - Set SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID
           and SAI_FDB_FLUSH_ATTR_BV_ID
        5) Flush all static entries by bridge port and VLAN - Set SAI_FDB_FLUSH_ATTR_ENTRY_TYPE,
           SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID, and SAI_FDB_FLUSH_ATTR_BV_ID
        """
        if attrs is None:
            attrs = ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_ALL"]
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate("SAI_OBJECT_TYPE_SWITCH:" + self.oid, attrs, "Sflush")
        assert status[0].decode("utf-8") == 'Sflushresponse'
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    def clear_stats(self, obj, attrs, do_assert = True):
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sclear_stats")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'
        return status[2]

    def get_stats(self, obj, attrs, do_assert = True):
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sget_stats")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'

        data = SaiData(status[1].decode("utf-8"))
        if do_assert:
            return data

        return status[2], data

    def create_fdb(self, vlan_oid, mac, bp_oid, action = "SAI_PACKET_ACTION_FORWARD"):
        self.create('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.oid
                       }
                   ),
                   [
                       "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                       "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_oid,
                       "SAI_FDB_ENTRY_ATTR_PACKET_ACTION",  action
                   ])

    def remove_fdb(self, vlan_oid, mac, do_assert = True):
        self.remove('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.oid
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
        assert vlan_oid.startswith("oid:")

        vlan_mbr_oids = []
        status, data = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST", "1:oid:0x0"], False)
        if status == "SAI_STATUS_SUCCESS":
            vlan_mbr_oids = data.oids()
        elif status == "SAI_STATUS_BUFFER_OVERFLOW":
            oids = self.make_list(data.uint32(), "oid:0x0")
            vlan_mbr_oids = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST", oids]).oids()
        else:
            assert status == "SAI_STATUS_SUCCESS"

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
                             "switch_id": self.oid,
                             "vr":        vrf_oid
                        }
                   ), attrs)

    def remove_route(self, dest, vrf_oid):
        self.remove('SAI_OBJECT_TYPE_ROUTE_ENTRY:' + json.dumps(
                       {
                           "dest":      dest,
                           "switch_id": self.oid,
                           "vr":        vrf_oid
                       })
                    )

    def hostif_dataplane_start(self, ifaces):
        self.hostif_map = dict()

        # Start ptf_nn_agent.py on DUT
        if self.remote_iface_agent_start(ifaces) == False:
            return None

        for inum, iname in ifaces.items():
            socket_addr = 'tcp://{}:10001'.format(self.server_ip)
            self.hostif_map[(0, int(inum))] = socket_addr
            assert self.remote_iface_is_up(iname), f"Interface {iname} must be up before dataplane init."

        self.hostif_dataplane = SaiHostifDataPlane(self.exec_params, ifaces, self.server_ip)
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
            self.remove(self.port_oids[idx])
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

        # Create ports as per SKU
        for fp_port in sorted(sku["port"], key=int):
            port_attr = [
                "SAI_PORT_ATTR_ADMIN_STATE",   "true",
                "SAI_PORT_ATTR_PORT_VLAN_ID",  self.default_vlan_id,
            ]

            # Lanes
            lanes = sku["port"][fp_port]["lanes"]
            lanes = str(lanes.count(',') + 1) + ":" + lanes
            port_attr.append("SAI_PORT_ATTR_HW_LANE_LIST")
            port_attr.append(lanes)

            # Speed
            speed = sku["port"][fp_port]["speed"] if "speed" in sku["port"][fp_port] else sku["speed"]
            port_attr.append("SAI_PORT_ATTR_SPEED")
            port_attr.append(speed)

            # Autoneg
            autoneg = sku["port"][fp_port]["autoneg"] if "autoneg" in sku["port"][fp_port] else sku["autoneg"]
            autoneg = "true" if autoneg == "on" else "false"
            port_attr.append("SAI_PORT_ATTR_AUTO_NEG_MODE")
            port_attr.append(autoneg)

            # FEC
            fec = sku["port"][fp_port]["fec"] if "fec" in sku["port"][fp_port] else sku["fec"]
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
            self.create_vlan_member(self.default_vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

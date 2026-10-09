import glob
import json
import os
import re
import time

from saichallenger.common.sai import Sai
from saichallenger.common.sai_data import SaiData, SaiObjType
from saichallenger.common.sai_dataplane.sai_hostif_dataplane import SaiHostifDataPlane


class SaiNpu(Sai):
    """
    SAI NPU (Network Processing Unit) interface.

    Extends the base Sai class with NPU-specific functionality for managing
    network forwarding elements like FDB entries, VLAN members, and routes.
    """

    def __init__(self, cfg):
        cfg["client"]["config"]["asic_type"] = "npu"
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
                with open(f"{self.asic_dir}/{self.target}/sku/{self.sku}.json") as f:
                    self.sku_config = json.load(f)
            except Exception as e:
                assert False, f"{e}"

        sw_attr = attr.copy()
        sw_attr.append("SAI_SWITCH_ATTR_INIT_SWITCH")
        sw_attr.append("true")
        # @default SAI_SWITCH_TYPE_NPU

        self.switch_oid = self.create(SaiObjType.SWITCH, sw_attr)
        self.rec2vid[self.switch_oid] = self.switch_oid

        # Default .1Q bridge
        self.dot1q_br_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID"]).oid()
        assert self.dot1q_br_oid != "oid:0x0"

        # Default VLAN
        self.default_vlan_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID"]).oid()
        assert self.default_vlan_oid != "oid:0x0"

        self.default_vlan_id = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID"]).value()
        assert self.default_vlan_id != "0"

        # Default VRF
        self.default_vrf_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID"]).oid()
        assert self.default_vrf_oid != "oid:0x0"

        # Ports
        port_num = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS"]).uint32()
        if port_num > 0:
            self.port_oids = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_PORT_LIST"]).to_list()

            # .1Q bridge ports
            self.dot1q_bp_oids = self.get(self.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST"]).to_list()
            assert len(self.dot1q_bp_oids) > 0
            assert self.dot1q_bp_oids[0].startswith("oid:")

            if self.sku_config is None:
                # The ports will not be re-created.
                # Make sure the bridge ports are added into the default VLAN.
                for bp_oid in self.dot1q_bp_oids:
                    vlan_mbr_oid = self.get_vlan_member(self.default_vlan_oid, bp_oid)
                    if vlan_mbr_oid is None:
                        self.create_vlan_member(self.default_vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        # Update SKU
        if self.sku_config is not None:
            self.set_sku_mode(self.sku_config)

        # Wait for ports oper up state
        if self.run_traffic:
            cpu_port_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_CPU_PORT"]).oid()
            for port_oid in self.port_oids:
                admin_state = self.get(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE"]).value()
                if port_oid != cpu_port_oid and admin_state == "true":
                    self.assert_port_oper_up(port_oid)

    def cleanup(self):
        super().cleanup()
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

    def reset(self):
        self.cleanup()
        attr = []
        self.init(attr)

    def perform_warm_reboot(self, pre_tout=30, warm_tout=30, after_warm_tout=5):
        # disable FDB aging and learning for the switch and bridge ports
        switch_fdb_aging_time = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME"]).value()
        self.set(self.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", "0"], do_assert=True)
        for bp_oid in self.dot1q_bp_oids:
            self.set(bp_oid, ["SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE", "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE"], do_assert=True)

        super().perform_warm_reboot(pre_tout=pre_tout, warm_tout=warm_tout, after_warm_tout=after_warm_tout)
        self._verify_warm_boot()

        # restore FDB aging and learning for the switch and bridge ports
        for bp_oid in self.dot1q_bp_oids:
            self.set(bp_oid, ["SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE", "SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW"], do_assert=True)
        self.set(self.switch_oid, ["SAI_SWITCH_ATTR_FDB_AGING_TIME", switch_fdb_aging_time], do_assert=True)


    
    def _verify_warm_boot(self):
        switch_type = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_TYPE"]).value()
        assert switch_type == "SAI_SWITCH_TYPE_NPU", "Switch type is not NPU"

        dot1q_br_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID"]).oid()
        assert dot1q_br_oid == self.dot1q_br_oid, "Default .1Q bridge ID is not the same"

        default_vlan_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID"]).oid()
        assert default_vlan_oid == self.default_vlan_oid, "Default VLAN ID is not the same"

        default_vlan_id = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID"]).value()
        assert default_vlan_id == self.default_vlan_id, "Default VLAN ID is not the same"

        default_vrf_oid = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID"]).oid()
        assert default_vrf_oid == self.default_vrf_oid, "Default VRF ID is not the same"

        port_oids = self.get(self.switch_oid, ["SAI_SWITCH_ATTR_PORT_LIST"]).to_list()
        assert port_oids == self.port_oids, "Port list is not the same"

        dot1q_bp_oids = self.get(self.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST"]).to_list()
        assert dot1q_bp_oids == self.dot1q_bp_oids, "Bridge port list is not the same"


    def create_fdb(self, vlan_oid, mac, bp_oid, entry_type="SAI_FDB_ENTRY_TYPE_STATIC", action="SAI_PACKET_ACTION_FORWARD", do_assert=True):
        return self.create(
                   self.fdb_entry_key(vlan_oid, mac),
                   [
                       "SAI_FDB_ENTRY_ATTR_TYPE",           entry_type,
                       "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_oid,
                       "SAI_FDB_ENTRY_ATTR_PACKET_ACTION",  action
                   ],
                   do_assert)

    def remove_fdb(self, vlan_oid, mac, do_assert=True):
        return self.remove(self.fdb_entry_key(vlan_oid, mac), do_assert)

    def create_vlan_member(self, vlan_oid, bp_oid, tagging_mode):
        oid = self.create(SaiObjType.VLAN_MEMBER,
                    [
                        "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           vlan_oid,
                        "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    bp_oid,
                        "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", tagging_mode
                    ])
        return oid

    def get_vlan_member(self, vlan_oid, bp_oid):
        vlan_mbr_oids = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST"]).to_list()
        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID"]).oid()
            if oid == bp_oid:
                return vlan_mbr_oid
        return None

    def remove_vlan_member(self, vlan_oid, bp_oid):
        vlan_mbr_oid = self.get_vlan_member(vlan_oid, bp_oid)
        assert vlan_mbr_oid, f"Bridge Port {bp_oid} is not a member of VLAN {vlan_oid}"
        self.remove(vlan_mbr_oid)

    def remove_bridge_port(self, bp_oid):
        """Remove a bridge port using the SAI-required teardown sequence.

        Per the SAI comment on SAI_BRIDGE_PORT_ATTR_ADMIN_STATE:
            Before removing a bridge port, need to disable it by setting admin mode 
            to false, then flush the FDB entries, and then remove it.

        This helper flushes only dynamic FDB entries for the given bridge port.
        Static entries must be deleted by the caller beforehand.
        """
        self.set(bp_oid, ["SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "false"])
        self.flush_fdb_entries(self.switch_oid, 
                               ["SAI_FDB_FLUSH_ATTR_ENTRY_TYPE", "SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC",
                                "SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID", bp_oid])
        self.remove(bp_oid)

    def _route_entry_key(self, vr_oid, prefix):
        return "SAI_OBJECT_TYPE_ROUTE_ENTRY:" + json.dumps(
            {
                "dest": prefix,
                "switch_id": self.switch_oid,
                "vr": vr_oid,
            }
        )
    
    def create_route(self, dest, vrf_oid, nh_oid=None, opt_attr=None):
        attrs = []
        if nh_oid:
            attrs += ["SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID", nh_oid]
        if opt_attr is None:
            opt_attr = []
        attrs += opt_attr
        self.create(self._route_entry_key(vrf_oid, dest), attrs)

    def remove_route(self, dest, vrf_oid):
        self.remove(self._route_entry_key(vrf_oid, dest))

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
            oid =  self.get_vlan_member(self.default_vlan_oid, self.dot1q_bp_oids[idx])
            if oid:
                self.remove(oid)
            self.remove_bridge_port(self.dot1q_bp_oids[idx])
            status, data = self.get(self.port_oids[idx], ["SAI_PORT_ATTR_PORT_SERDES_ID"], do_assert=False)
            if status == "SAI_STATUS_SUCCESS" and data.oid() != "oid:0x0":
                self.remove(data.oid())
            self.remove(self.port_oids[idx])
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

        # Create ports as per SKU
        for port in sku["port"]:
            port_attr = [
                "SAI_PORT_ATTR_ADMIN_STATE",   "true",
                "SAI_PORT_ATTR_PORT_VLAN_ID",  self.default_vlan_id,
                # To make saivs happy on ports re-creation
                # https://github.com/sonic-net/sonic-sairedis/blob/00a953c6eafb8852d771c0f7a4f91db9f0965530/vslib/SwitchStateBase.cpp#L1207
                "SAI_PORT_ATTR_MTU",           "1514",
            ]

            # Lanes
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

            port_oid = self.create(SaiObjType.PORT, port_attr)
            self.port_oids.append(port_oid)

        # To make saivs happy on ports re-creation
        # This will cause refresh_port_list() to update READ_ONLY attribute
        # which is needed for refresh_bridge_port_list()
        self.get(self.switch_oid, ["SAI_SWITCH_ATTR_PORT_LIST"])

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
        vlan_mbr_oids = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST"]).to_list()
        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID"]).oid()
            default_vlan_bp.append(oid)

        for oid in self.dot1q_bp_oids:
            if oid not in default_vlan_bp:
                self.create_vlan_member(self.default_vlan_oid, oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")


    def rebreak_port(self, cases, autoneg="off", fec="none"):
        target_lanes = ",".join(c["lanes"] for c in cases)
        target = set(target_lanes.split(","))
        keep, drop = [], []

        for port_oid, bp_oid in zip(self.port_oids, self.dot1q_bp_oids):
            status, data = self.get(port_oid, ["SAI_PORT_ATTR_HW_LANE_LIST", self.make_list(8, "0")], do_assert=False)
            lanes = set(data.to_list()) if status == "SAI_STATUS_SUCCESS" and data else set()
            (drop if lanes & target else keep).append((port_oid, bp_oid))

        for port_oid, bp_oid in drop:
            vlan_mbr = self.get_vlan_member(self.default_vlan_oid, bp_oid)
            if vlan_mbr:
                self.remove(vlan_mbr)
            self.remove_bridge_port(bp_oid)
            status, data = self.get(port_oid, ["SAI_PORT_ATTR_PORT_SERDES_ID"], do_assert=False)
            if status == "SAI_STATUS_SUCCESS" and data.oid() != "oid:0x0":
                self.remove(data.oid())
            self.remove(port_oid)

        created = []
        for port in cases:
            lanes = port["lanes"]
            lanes_attr = f"{lanes.count(',') + 1}:{lanes}"
            speed = str(port.get("speed_mbps", port.get("speed", "100000")))

            port_attr = [
                "SAI_PORT_ATTR_ADMIN_STATE", "true",
                "SAI_PORT_ATTR_PORT_VLAN_ID", self.default_vlan_id,
                "SAI_PORT_ATTR_MTU", "1514",
                "SAI_PORT_ATTR_HW_LANE_LIST", lanes_attr,
                "SAI_PORT_ATTR_SPEED", speed,
                "SAI_PORT_ATTR_AUTO_NEG_MODE", "true" if autoneg == "on" else "false",
                "SAI_PORT_ATTR_FEC_MODE", "SAI_PORT_FEC_MODE_" + fec.upper(),
            ]

            port_oid = self.create(SaiObjType.PORT, port_attr)
            created.append(port_oid)

        created_bps = []
        for port_oid in created:
            bp_oid = self.create(SaiObjType.BRIDGE_PORT, [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", port_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
            ])
            created_bps.append(bp_oid)

        default_vlan_bp = []
        vlan_mbr_oids = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST"]).to_list()
        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID"]).oid()
            default_vlan_bp.append(oid)

        for oid in created_bps:
            if oid not in default_vlan_bp:
                self.create_vlan_member(self.default_vlan_oid, oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")

        self.port_oids = [oid for oid, _ in keep] + created
        self.dot1q_bp_oids = [bp for _, bp in keep] + created_bps
        return created

    def assert_port_oper_up(self, port_oid, tout=15):
        for i in range(tout):
            data = self.get(port_oid, ["SAI_PORT_ATTR_OPER_STATUS"])
            if data.value() == "SAI_PORT_OPER_STATUS_UP":
                return
            if i + 1 < tout:
                time.sleep(1)
        assert False, f"The port {port_oid} is still down after {tout} seconds..."

    def _neighbor_entry_key(npu, rif_oid, ip):
        return "SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + json.dumps(
            {
                "ip_address": ip,
                "rif_id": rif_oid,
                "switch_id": npu.switch_oid,
            }
        )

    def ipmc_entry_key(self, vr_oid, src_ip, dst_ip, entry_type=0):
        return "SAI_OBJECT_TYPE_IPMC_ENTRY:" + json.dumps(
            {
                "switch_id": self.switch_oid,
                "vr_id": vr_oid,
                "type": str(entry_type),
                "destination": dst_ip,
                "source": src_ip,
            }
        )

    def fdb_entry_key(self, vlan_oid, mac):
        return "SAI_OBJECT_TYPE_FDB_ENTRY:" + json.dumps(
            {
                "bvid": vlan_oid,
                "mac": mac,
                "switch_id": self.switch_oid,
            }
        )

    def my_sid_entry_key(self, vr_oid, sid, locator_block_len=48, locator_node_len=16,
                         function_len=0, args_len=0):
        return "SAI_OBJECT_TYPE_MY_SID_ENTRY:" + json.dumps(
            {
                "switch_id": self.switch_oid,
                "vr_id": vr_oid,
                "locator_block_len": str(locator_block_len),
                "locator_node_len": str(locator_node_len),
                "function_len": str(function_len),
                "args_len": str(args_len),
                "sid": sid,
            }
        )

    @staticmethod
    def get_port_breakout_modes(port_name=None, breakout_mode=None, npu=None, base_dir=None, testbed=None):
        """
        Parse platform.json and return breakout configuration as Python data.

        Each port dict has keys name, index, lanes, modes.
        Each mode maps to a list of per-logical-port dicts with
        index, name, mode, alias, lanes, speed_mbps, supported_speeds_mbps.
        """
        platform_json = None
        if npu is not None:
            base = f"{npu.asic_dir}/{npu.target}"
            cfg_names = (npu.cfg.get("platform"), npu.sku)
        elif base_dir is not None and testbed is not None:
            with open(os.path.join(base_dir, "testbeds", f"{testbed}.json")) as f:
                npu_cfg = json.load(f)["npu"][0]
            matches = glob.glob(f"{base_dir}/npu/**/{npu_cfg['asic']}", recursive=True)
            if not matches:
                return {}
            base = os.path.join(matches[0], npu_cfg["target"])
            cfg_names = (npu_cfg.get("platform"), npu_cfg.get("sku"))
        else:
            return {}

        # resolve platform.json from testbed "platform" then "sku" key
        for name in cfg_names:
            if name:
                path = os.path.join(base, "platform", f"{name}.json")
                if os.path.isfile(path):
                    platform_json = path
                    break
        if platform_json is None:
            path = os.path.join(base, "platform.json")
            platform_json = path if os.path.isfile(path) else None

        if not platform_json or not os.path.isfile(platform_json):
            return {}

        brkout_pattern = re.compile(r"(\d{1,6})x(\d+(?:\.\d+)?G?)(\[([^\]]+)\])?(\((\d{1,6})\))?")

        with open(platform_json) as f:
            interfaces = json.load(f).get("interfaces", {})

        if port_name is not None and port_name not in interfaces:
            raise ValueError(f"unknown port {port_name}")

        ports = interfaces if port_name is None else {port_name: interfaces[port_name]}
        result = {}

        # each physical port from platform.json interfaces
        for name, port in ports.items():
            lane_list = port["lanes"].split(",")
            index_list = port["index"].split(",")
            modes = {}

            # each breakout mode string (e.g. 1x25G, 4x10G+1x40G)
            for mode_name, logical_port_names in port["breakout_modes"].items():
                segments = []
                # compound modes: split on '+' (e.g. 4x10G+1x40G)
                for part in mode_name.split("+"):
                    match = brkout_pattern.match(part)
                    if not match:
                        raise ValueError(f"unsupported breakout mode segment: {part}")

                    default_speed = match.group(2).strip()
                    default_speed_mbps = (int(float(default_speed[:-1]) * 1000) if default_speed.endswith("G") else int(default_speed))
                    supported_speeds_mbps = {default_speed_mbps}
                    if match.group(4):
                        # optional [speed,speed,...] bracket list
                        for speed in match.group(4).split(","):
                            speed = speed.strip()
                            supported_speeds_mbps.add(int(float(speed[:-1]) * 1000) if speed.endswith("G") else int(speed))

                    segments.append({
                        "num_ports": int(match.group(1)),
                        "num_assigned_lanes": int(match.group(6)) if match.group(6) else len(lane_list),
                        "default_speed_mbps": default_speed_mbps,
                        "supported_speeds_mbps": sorted(supported_speeds_mbps),
                    })

                lanes_used = sum(s["num_assigned_lanes"] for s in segments)
                if lanes_used > len(lane_list):
                    raise ValueError(
                        f"{name} mode {mode_name}: assigned lanes {lanes_used} "
                        f"exceed available {len(lane_list)}"
                    )

                num_logical_ports = sum(s["num_ports"] for s in segments)
                if num_logical_ports != len(logical_port_names):
                    raise ValueError(
                        f"{name} mode {mode_name}: expected {len(logical_port_names)} "
                        f"aliases, breakout defines {num_logical_ports}"
                    )

                logical_ports = []
                lane_id = 0
                alias_id = 0
                # map parsed segments to logical port entries
                for segment in segments:
                    lanes_per_port = segment["num_assigned_lanes"] // segment["num_ports"]
                    # one entry per logical port in the segment
                    for _ in range(segment["num_ports"]):
                        lane_end = lane_id + lanes_per_port
                        logical_ports.append({
                            "index": int(index_list[lane_id]),
                            "name": name,
                            "mode": mode_name,
                            "alias": logical_port_names[alias_id],
                            "lanes": ",".join(lane_list[lane_id:lane_end]),
                            "speed_mbps": segment["default_speed_mbps"],
                            "supported_speeds_mbps": segment["supported_speeds_mbps"],
                        })
                        lane_id += lanes_per_port
                        alias_id += 1
                modes[mode_name] = logical_ports

            result[name] = {
                "name": name,
                "index": int(index_list[0]),
                "lanes": port["lanes"],
                "modes": modes,
            }

        if breakout_mode is not None:
            return result[port_name]["modes"][breakout_mode]

        return result if port_name is None else result[port_name]
"""
SAI Challenger topology compatibility layer.

Reproduces the standard L2/L3 layout so migrated pytest cases can use
familiar attribute names while calling the Challenger ``SaiNpu`` API.

Quick reference - attribute mapping:

+---------------------------+--------------------------------------------------+
| Old pattern               | Challenger                                       |
+===========================+==================================================+
| ``self.client``           | ``npu`` (``SaiNpu`` - passed into setup)         |
| ``self.switch_id``        | ``npu.switch_oid`` / alias ``topo.switch_id``    |
| ``self.port_list`` / OID  | ``npu.port_oids[i]`` / alias ``topo.port{i}``    |
| ``self.default_vrf``      | ``npu.default_vrf_oid`` / ``topo.default_vrf``   |
| ``self.default_vlan_id``  | ``npu.default_vlan_id`` / ``topo.default_vlan_id``|
| ``self.default_1q_bridge``| ``npu.dot1q_br_oid`` / ``topo.default_1q_bridge``|
| ``sai_thrift_create_*``   | ``npu.create(SaiObjType.X, [attr, val, ...])``   |
| ``sai_thrift_remove_*``   | ``npu.remove(oid)``                              |
| ``sai_thrift_set_*``      | ``npu.set(oid, [attr, val])``                    |
| ``sai_thrift_get_*``      | ``npu.get(oid, [attr, ...])``                    |
| ``self.dataplane``        | pytest fixture ``dataplane``                     |
+---------------------------+--------------------------------------------------+

Ports configuration (U/T = untagged/tagged VLAN member):

+--------+------+-----------+-------------+--------+------------+------------+
| Port   | LAG  | _member   | Bridge port | VLAN   | _member    | RIF        |
+========+======+===========+=============+========+============+============+
| port0  |      |           | port0_bp    | vlan10 | _member0 U |            |
| port1  |      |           | port1_bp    |        | _member1 T |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port2  |      |           | port2_bp    | vlan20 | _member0 U |            |
| port3  |      |           | port3_bp    |        | _member1 T |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port4  | lag1 | _member4  | lag1_bp     | vlan10 | _member2 U |            |
| port5  |      | _member5  |             |        |            |            |
| port6  |      | _member6  |             |        |            |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port7  | lag2 | _member7  | lag2_bp     | vlan20 | _member2 T |            |
| port8  |      | _member8  |             |        |            |            |
| port9  |      | _member9  |             |        |            |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port10 |      |           |             |        |            | port10_rif |
| port11 |      |           |             |        |            | port11_rif |
| port12 |      |           |             |        |            | port12_rif |
| port13 |      |           |             |        |            | port13_rif |
+--------+------+-----------+-------------+--------+------------+------------+
| port14 | lag3 | _member14 |             |        |            | lag3_rif   |
| port15 |      | _member15 |             |        |            |            |
| port16 |      | _member16 |             |        |            |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port17 | lag4 | _member17 |             |        |            | lag4_rif   |
| port18 |      | _member18 |             |        |            |            |
| port19 |      | _member19 |             |        |            |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port20 |      |           | port20_bp   | vlan30 | _member0 U | vlan30_rif |
| port21 |      |           | port21_bp   |        | _member1 T |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port22 | lag5 | _member22 | lag5_bp     | vlan30 | _member2 T |            |
| port23 |      | _member23 |             |        |            |            |
+--------+------+-----------+-------------+--------+------------+------------+
| port24 |                                                                   |
| port25 |                                                                   |
| port26 |                                                                   |
| port27 |                        UNASSIGNED                                 |
| port28 |                                                                   |
| port29 |                                                                   |
| port30 |                                                                   |
| port31 |                                                                   |
+--------+-------------------------------------------------------------------+
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, List

import pytest

from saichallenger.common.sai_data import SaiObjType


class SaiPtfTopologyMixin:
    """
    Topology builder for SAI Challenger NPU.

    Sets up a standard L2/L3 switch layout and exposes named aliases
    (port0, lag1, vlan10, port10_rif, ...) so test code stays readable.
    """

    npu: Any
    switch_id: str
    default_vrf: str
    default_vlan_oid: str
    default_vlan_id: str
    default_1q_bridge: str

    def setup_ptf_topology(self, npu: Any) -> None:
        """Initialize NPU reference, build aliases and bring up the full topology."""
        self.npu = npu
        self.def_bridge_port_list = []
        self.def_lag_list = []
        self.def_lag_member_list = []
        self.def_vlan_list = []
        self.def_vlan_member_list = []
        self.def_rif_list = []
        self._saved_default_vlan_members: List[Dict[str, str]] = []

        self.switch_id = npu.switch_oid
        self.default_vrf = npu.default_vrf_oid
        self.default_vlan_oid = npu.default_vlan_oid
        self.default_vlan_id = npu.default_vlan_id
        self.default_1q_bridge = npu.dot1q_br_oid

        if len(npu.port_oids) < 24:
            pytest.skip(
                "SaiPtfTopologyMixin requires at least 24 active ports (indices 0 through 23)"
            )

        for i in range(24):
            setattr(self, "port%d" % i, npu.port_oids[i])

        self.remove_default_vlan_members()
        self.remove_default_bridge_ports()
        self.create_sai_helper_topology()

    def teardown_ptf_topology(self) -> None:
        """Tear down topology in the correct SAI order and restore default VLAN state."""
        self.npu.set(self.port2, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])
        self.npu.set(self.lag1, ["SAI_LAG_ATTR_PORT_VLAN_ID", "0"])
        self.npu.set(self.port0, ["SAI_PORT_ATTR_PORT_VLAN_ID", "0"])

        self.destroy_default_routes()
        self.destroy_routing_interfaces()
        self.destroy_vlans_with_members()
        self.destroy_bridge_ports()
        self.destroy_lags_with_members()
        self.restore_default_bridge_ports()
        self.restore_default_vlan_members()

    def remove_default_bridge_ports(self) -> None:
        """Remove default 1Q bridge ports."""
        for idx in list(range(len(self.npu.port_oids))):
            bp = self.npu.dot1q_bp_oids[idx]
            self.npu.remove(bp)

    def remove_default_vlan_members(self) -> None:
        """Detach all ports from the default VLAN and save them for later restore."""
        vlan_oid = self.npu.default_vlan_oid
        mbr_oids = self.npu.get_list(vlan_oid, "SAI_VLAN_ATTR_MEMBER_LIST", "oid:0x0")
        self._saved_default_vlan_members = []
        for mbr_oid in mbr_oids:
            bp_oid = self.npu.get(mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID"]).oid()
            port_oid = self.npu.get(bp_oid, ["SAI_BRIDGE_PORT_ATTR_PORT_ID"]).oid()
            tag = self.npu.get(mbr_oid, ["SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE"]).value()
            self._saved_default_vlan_members.append({"port_oid": port_oid, "tagging": tag})
            self.npu.remove(mbr_oid)

    def restore_default_bridge_ports(self) -> None:
        """Re-create default bridge ports."""
        for rec in self._saved_default_vlan_members:
            bp_oid = self.npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", rec["port_oid"],
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true"
                ]
            )
            rec.update({"port_oid": bp_oid})
        self.npu.dot1q_bp_oids = self.npu.get(self.npu.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST"]).to_list()

    def restore_default_vlan_members(self) -> None:
        """Re-attach ports to the default VLAN as they were before setup."""
        for rec in self._saved_default_vlan_members:
            self.npu.create_vlan_member(
                self.npu.default_vlan_oid, rec["port_oid"], rec["tagging"]
            )

    @staticmethod
    def _tagging_mode(tag: str) -> str:
        if tag.startswith("SAI_VLAN_TAGGING_MODE_"):
            return tag
        t = tag.lower()
        if t == "untagged":
            return "SAI_VLAN_TAGGING_MODE_UNTAGGED"
        if t == "tagged":
            return "SAI_VLAN_TAGGING_MODE_TAGGED"
        raise ValueError("tagging_mode_string must be 'untagged', 'tagged', or SAI_VLAN_TAGGING_MODE_*")

    def create_bridge_ports(self, ports: List[int]) -> None:
        """Create bridge ports for the given port indices and expose them as portN_bp."""
        for port_index in ports:
            port_oid = getattr(self, "port%d" % port_index)
            bp_oid = self.npu.create(
                SaiObjType.BRIDGE_PORT,
                [
                    "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                    "SAI_BRIDGE_PORT_ATTR_PORT_ID", port_oid,
                    "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
                ],
            )
            setattr(self, "port%d_bp" % port_index, bp_oid)
            self.def_bridge_port_list.append(bp_oid)

    def create_lag_with_members(self, lag_index: int, ports: List[int]) -> None:
        """Create a LAG with its bridge port and member ports; expose as lagN / lagN_bp / lagN_memberM."""
        lag_oid = self.npu.create(SaiObjType.LAG, [])
        setattr(self, "lag%d" % lag_index, lag_oid)
        self.def_lag_list.append(lag_oid)

        lag_bp = self.npu.create(
            SaiObjType.BRIDGE_PORT,
            [
                "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
                "SAI_BRIDGE_PORT_ATTR_PORT_ID", lag_oid,
                "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
            ],
        )
        setattr(self, "lag%d_bp" % lag_index, lag_bp)
        self.def_bridge_port_list.append(lag_bp)

        for member_index in ports:
            port_oid = getattr(self, "port%d" % member_index)
            lm_oid = self.npu.create(
                SaiObjType.LAG_MEMBER,
                [
                    "SAI_LAG_MEMBER_ATTR_LAG_ID", lag_oid,
                    "SAI_LAG_MEMBER_ATTR_PORT_ID", port_oid,
                ],
            )
            setattr(self, "lag%d_member%d" % (lag_index, member_index), lm_oid)
            self.def_lag_member_list.append(lm_oid)

    def create_vlan_with_members(self, vlan_id: int, members: Dict[str, str]) -> None:
        """
        Create a VLAN and attach bridge ports to it.

        members: {bp_oid: 'untagged' | 'tagged'}
        Exposes vlan{id}, vlan{id}_member0, vlan{id}_member1, ...
        """
        vlan_oid = self.npu.create(
            SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", str(vlan_id)]
        )
        setattr(self, "vlan%d" % vlan_id, vlan_oid)
        self.def_vlan_list.append(vlan_oid)

        idx = 0
        for bp_oid, tag in members.items():
            tag_mode = self._tagging_mode(tag)
            vm_oid = self.npu.create_vlan_member(vlan_oid, bp_oid, tag_mode)
            setattr(self, "vlan%d_member%d" % (vlan_id, idx), vm_oid)
            self.def_vlan_member_list.append(vm_oid)
            idx += 1

    def create_routing_interfaces(self, rif_configs: List[Dict[str, Any]]) -> None:
        """
        Create router interfaces from a list of config dicts.

        Each dict needs 'type' ('vlan'|'lag'|'port') and 'port_or_vlan' index.
        Optional 'vrf' defaults to the switch default VRF.
        Exposes vlan30_rif, lag3_rif, port10_rif, etc.
        """
        for cfg in rif_configs:
            rif_type = cfg["type"]
            pv = cfg["port_or_vlan"]
            vrf = cfg.get("vrf")
            if vrf is None:
                vrf = self.default_vrf

            if rif_type == "vlan":
                vlan_oid = getattr(self, "vlan%d" % pv)
                rif_oid = self.npu.create(
                    SaiObjType.ROUTER_INTERFACE,
                    [
                        "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", vrf,
                        "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_VLAN",
                        "SAI_ROUTER_INTERFACE_ATTR_VLAN_ID", vlan_oid,
                    ],
                )
                setattr(self, "vlan%d_rif" % pv, rif_oid)
            elif rif_type == "lag":
                lag_oid = getattr(self, "lag%d" % pv)
                rif_oid = self.npu.create(
                    SaiObjType.ROUTER_INTERFACE,
                    [
                        "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", vrf,
                        "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_PORT",
                        "SAI_ROUTER_INTERFACE_ATTR_PORT_ID", lag_oid,
                    ],
                )
                setattr(self, "lag%d_rif" % pv, rif_oid)
            elif rif_type == "port":
                port_oid = getattr(self, "port%d" % pv)
                rif_oid = self.npu.create(
                    SaiObjType.ROUTER_INTERFACE,
                    [
                        "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", vrf,
                        "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_PORT",
                        "SAI_ROUTER_INTERFACE_ATTR_PORT_ID", port_oid,
                    ],
                )
                setattr(self, "port%d_rif" % pv, rif_oid)
            else:
                raise ValueError("rif_configs type must be 'vlan', 'lag', or 'port'")

            self.def_rif_list.append(rif_oid)

    def destroy_bridge_ports(self) -> None:
        """Remove bridge ports in reverse creation order."""
        for bridge_port in reversed(self.def_bridge_port_list):
            self.npu.remove(bridge_port)
        self.def_bridge_port_list.clear()

    def destroy_lags_with_members(self) -> None:
        """Remove LAG members first, then the LAG objects themselves."""
        for lag_member in self.def_lag_member_list:
            self.npu.remove(lag_member)
        self.def_lag_member_list.clear()

        for lag_oid in self.def_lag_list:
            self.npu.remove(lag_oid)
        self.def_lag_list.clear()

    def destroy_vlans_with_members(self) -> None:
        """Remove VLAN members first, then the VLAN objects themselves."""
        for vlan_member in self.def_vlan_member_list:
            self.npu.remove(vlan_member)
        self.def_vlan_member_list.clear()

        for vlan_oid in self.def_vlan_list:
            self.npu.remove(vlan_oid)
        self.def_vlan_list.clear()

    def destroy_routing_interfaces(self) -> None:
        """Remove router interfaces in reverse creation order."""
        for rif_oid in reversed(self.def_rif_list):
            self.npu.remove(rif_oid)
        self.def_rif_list.clear()

    def create_default_routes(self) -> None:
        """Add default IPv4 and IPv6 drop routes in the switch default VRF."""
        self.npu.create_route(
            "0.0.0.0/0",
            self.default_vrf,
            None,
            ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"],
        )
        self.npu.create_route(
            "::/0",
            self.default_vrf,
            None,
            ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_DROP"],
        )

    def destroy_default_routes(self) -> None:
        """Remove the default drop routes added during setup."""
        self.npu.remove_route("0.0.0.0/0", self.default_vrf)
        self.npu.remove_route("::/0", self.default_vrf)

    def create_sai_helper_topology(self) -> None:
        """Build the full port/VLAN/LAG/RIF layout as described in the module docstring."""
        self.create_bridge_ports([0, 1, 2, 3, 20, 21])

        self.create_lag_with_members(1, [4, 5, 6])
        self.create_lag_with_members(2, [7, 8, 9])
        self.create_lag_with_members(3, [14, 15, 16])
        self.create_lag_with_members(4, [17, 18, 19])
        self.create_lag_with_members(5, [22, 23])

        self.create_vlan_with_members(
            10,
            {
                self.port0_bp: "untagged",
                self.port1_bp: "tagged",
                self.lag1_bp: "untagged",
            },
        )
        self.create_vlan_with_members(
            20,
            {
                self.port2_bp: "untagged",
                self.port3_bp: "tagged",
                self.lag2_bp: "untagged",
            },
        )
        self.create_vlan_with_members(
            30,
            {
                self.port20_bp: "untagged",
                self.port21_bp: "tagged",
                self.lag5_bp: "untagged",
            },
        )

        self.npu.set(self.port0, ["SAI_PORT_ATTR_PORT_VLAN_ID", "10"])
        self.npu.set(self.lag1, ["SAI_LAG_ATTR_PORT_VLAN_ID", "10"])
        self.npu.set(self.port2, ["SAI_PORT_ATTR_PORT_VLAN_ID", "20"])

        self.create_routing_interfaces(
            [
                {"type": "vlan", "port_or_vlan": 30},
                {"type": "lag", "port_or_vlan": 3},
                {"type": "lag", "port_or_vlan": 4},
                {"type": "port", "port_or_vlan": 10},
                {"type": "port", "port_or_vlan": 11},
                {"type": "port", "port_or_vlan": 12},
                {"type": "port", "port_or_vlan": 13},
            ]
        )

        self.create_default_routes()


class SaiPtfTopologyFixture(SaiPtfTopologyMixin):
    """Thin subclass used by the topology context manager."""

    pass


@contextmanager
def config(npu):
    topo = SaiPtfTopologyFixture()
    topo.setup_ptf_topology(npu)
    try:
        yield topo
    finally:
        topo.teardown_ptf_topology()

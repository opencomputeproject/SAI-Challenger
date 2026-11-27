
import pytest

from saichallenger.common.sai_data import SaiObjType


def encode_u8_list(value):
    encoded = value.encode("ascii")
    return f"{len(encoded)}:{','.join(str(byte) for byte in encoded)}"


OCS_PORTS = [
    ("1A", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("1B", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("2A", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("2B", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("3A", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("3B", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
]


OCS_PORT_ATTRIBUTES = [
    (
        "SAI_OCS_PORT_ATTR_OVERRIDE_STATE",
        "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL",
    ),
    (
        "SAI_OCS_PORT_ATTR_OVERRIDE_STATE",
        "SAI_OCS_PORT_OVERRIDE_STATE_FORCE_BLOCKED",
    ),
]


@pytest.fixture(scope="module")
def created_ocs_ports(npu):
    ports = {}

    for name, state in OCS_PORTS:
        oid = npu.create(
            SaiObjType.OCS_PORT,
            [
                "SAI_OCS_PORT_ATTR_NAME", encode_u8_list(name),
                "SAI_OCS_PORT_ATTR_OVERRIDE_STATE", state,
            ],
        )

        assert oid != "oid:0x0", f"Failed to create OCS port {name}"

        ports[name] = oid

    return ports


class TestOcsPort:

    @pytest.mark.parametrize(
        "attr, value",
        OCS_PORT_ATTRIBUTES,
        ids=[
            f"{attr.replace('SAI_OCS_PORT_ATTR_', '')}-{value.replace('SAI_OCS_PORT_OVERRIDE_STATE_', '')}"
            for attr, value in OCS_PORT_ATTRIBUTES
        ],
    )
    def test_ocs_port_attr(self, npu, created_ocs_ports, attr, value):
        for name, oid in created_ocs_ports.items():

            npu.set(oid, [attr, value])

            result = npu.get(oid, [attr])

            assert result.value() == value

    def test_ocs_port_oper_status_default_blocked(self, npu, created_ocs_ports):
        for name, oid in created_ocs_ports.items():
            npu.set(oid, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])
            result = npu.get(oid, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value()
            assert result == "SAI_OCS_PORT_STATUS_BLOCKED"

OCS_CROSS_CONNECTS = [
    ("1A", "1B"),
    ("2A", "2B"),
    ("3A", "3B"),
]


class TestOcsPortCrossConnect:

    @pytest.mark.parametrize(
        "ocs_port_a, ocs_port_b",
        OCS_CROSS_CONNECTS,
        ids=[
            f"{ocs_port_a}-{ocs_port_b}"
            for ocs_port_a, ocs_port_b in OCS_CROSS_CONNECTS
        ],
    )
    def test_ocs_port_cross_connect_create(self, npu, created_ocs_ports, ocs_port_a, ocs_port_b):
        ports = created_ocs_ports
        oid_a = ports[ocs_port_a]
        oid_b = ports[ocs_port_b]

        npu.set(oid_a, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])
        npu.set(oid_b, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])

        cross_connect_oid = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid_a,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid_b,
            ],
        )

        assert cross_connect_oid != "oid:0x0", f"Failed to create OCS cross connect {ocs_port_a}-{ocs_port_b}"

        oid_cross_a = npu.get(cross_connect_oid, ["SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID"]).value()
        assert oid_cross_a == oid_a, f"A side port ID mismatch for cross connect {ocs_port_a}-{ocs_port_b}"

        oid_cross_b = npu.get(cross_connect_oid, ["SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID"]).value()
        assert oid_cross_b == oid_b, f"B side port ID mismatch for cross connect {ocs_port_a}-{ocs_port_b}"

        assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"
        assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"

        npu.remove(cross_connect_oid)

        assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"
        assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"

    def test_ocs_cross_connect_same_port_rejected(self, npu, created_ocs_ports):
        ports = created_ocs_ports
        oid = ports["1A"]

        status, xc_oid = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid,
            ],
            do_assert=False,
        )

        assert status == "SAI_STATUS_INVALID_PARAMETER", f"Same-port cross-connect expected INVALID_PARAMETER, got {status}"

    def test_ocs_cross_connect_port_already_in_use(self, npu, created_ocs_ports):
        ports = created_ocs_ports
        oid_1a = ports["1A"]
        oid_1b = ports["1B"]
        oid_2a = ports["2A"]

        npu.set(oid_1a, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])
        npu.set(oid_1b, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])

        xc_oid = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid_1a,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid_1b,
            ],
        )

        assert xc_oid != "oid:0x0", f"Failed to create OCS cross connect {oid_1a}-{oid_1b}"

        status, _ = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid_2a,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid_1a,
            ],
            do_assert=False,
        )

        assert status == "SAI_STATUS_ITEM_ALREADY_EXISTS", f"Reusing port {oid_1a} expected ITEM_ALREADY_EXISTS, got {status}"

        npu.remove(xc_oid)

    def test_ocs_cross_connect_remove_and_reuse(self, npu, created_ocs_ports):
        ports = created_ocs_ports
        oid_1a = ports["1A"]
        oid_1b = ports["1B"]
        oid_2b = ports["2B"]

        for oid in (oid_1a, oid_1b, oid_2b):
            npu.set(oid, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])

        xc_oid = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid_1a,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid_1b,
            ],
        )

        assert xc_oid != "oid:0x0", f"Failed to create OCS cross connect {oid_1a}-{oid_1b}"

        npu.remove(xc_oid)

        assert npu.get(oid_1a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"
        assert npu.get(oid_1b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"

        xc_oid = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid_1a,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid_2b,
            ],
        )

        assert xc_oid != "oid:0x0", f"Failed to create OCS cross connect {oid_1a}-{oid_2b}"

        assert npu.get(oid_1a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"
        assert npu.get(oid_2b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"

        npu.remove(xc_oid)

    def test_ocs_port_force_blocked_with_cross_connect(self, npu, created_ocs_ports):
        ports = created_ocs_ports
        oid_a = ports["3A"]
        oid_b = ports["3B"]

        npu.set(oid_a, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])
        npu.set(oid_b, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])

        xc_oid = npu.create(
            SaiObjType.OCS_CROSS_CONNECT,
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", oid_a,
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", oid_b,
            ],
        )

        assert xc_oid != "oid:0x0", f"Failed to create OCS cross connect {oid_a}-{oid_b}"

        assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"
        assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"

        npu.set(oid_a, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_FORCE_BLOCKED"])

        assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"
        assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"

        npu.set(oid_a, ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])

        assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"
        assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"

        npu.remove(xc_oid)
        assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"
        assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_BLOCKED"


OCS_BULK_PORTS = [
    ("4A", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("4B", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("5A", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
    ("5B", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"),
]


OCS_BULK_CROSS_CONNECTS = [
    ("1A", "1B"),
    ("2A", "2B"),
    ("3A", "3B"),
]


class TestOcsPortBulk:

    def test_ocs_port_bulk_create(self, npu):
        attrs = [
            [
                "SAI_OCS_PORT_ATTR_NAME", encode_u8_list(name),
                "SAI_OCS_PORT_ATTR_OVERRIDE_STATE", state,
            ]
            for name, state in OCS_BULK_PORTS
        ]

        status, oids, entry_status = npu.bulk_create(
            SaiObjType.OCS_PORT,
            None,
            attrs,
            obj_count=len(attrs),
        )

        assert status == "SAI_STATUS_SUCCESS"
        assert all(s == "SAI_STATUS_SUCCESS" for s in entry_status)
        assert len(oids) == len(OCS_BULK_PORTS)

        for (name, _), oid in zip(OCS_BULK_PORTS, oids):
            assert oid != "oid:0x0", f"Failed to bulk create OCS port {name}"

            result = npu.get(oid, ["SAI_OCS_PORT_ATTR_NAME"]).value()
            assert result == encode_u8_list(name), \
                f"OCS port name mismatch for {name}: {result}"

            result = npu.get(oid, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value()
            assert result == "SAI_OCS_PORT_STATUS_BLOCKED", \
                f"OCS port {name} expected BLOCKED after bulk create, got {result}"

    def test_ocs_cross_connect_bulk_create(self, npu, created_ocs_ports):
        ports = created_ocs_ports

        for name_a, name_b in OCS_BULK_CROSS_CONNECTS:
            npu.set(ports[name_a], ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])
            npu.set(ports[name_b], ["SAI_OCS_PORT_ATTR_OVERRIDE_STATE", "SAI_OCS_PORT_OVERRIDE_STATE_NORMAL"])

        attrs = [
            [
                "SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID", ports[name_a],
                "SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID", ports[name_b],
            ]
            for name_a, name_b in OCS_BULK_CROSS_CONNECTS
        ]

        status, xc_oids, entry_status = npu.bulk_create(
            SaiObjType.OCS_CROSS_CONNECT,
            None,
            attrs,
            obj_count=len(attrs),
        )

        assert status == "SAI_STATUS_SUCCESS"
        assert all(s == "SAI_STATUS_SUCCESS" for s in entry_status)
        assert len(xc_oids) == len(OCS_BULK_CROSS_CONNECTS)

        for (name_a, name_b), xc_oid in zip(OCS_BULK_CROSS_CONNECTS, xc_oids):
            assert xc_oid != "oid:0x0", f"Failed to bulk create OCS cross connect {name_a}-{name_b}"

            oid_a = ports[name_a]
            oid_b = ports[name_b]

            assert npu.get(xc_oid, ["SAI_OCS_CROSS_CONNECT_ATTR_A_SIDE_PORT_ID"]).value() == oid_a
            assert npu.get(xc_oid, ["SAI_OCS_CROSS_CONNECT_ATTR_B_SIDE_PORT_ID"]).value() == oid_b
            assert npu.get(oid_a, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"
            assert npu.get(oid_b, ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == "SAI_OCS_PORT_STATUS_TUNED"

        status, entry_status = npu.bulk_remove(SaiObjType.OCS_CROSS_CONNECT, xc_oids)
        assert status == "SAI_STATUS_SUCCESS"
        assert all(s == "SAI_STATUS_SUCCESS" for s in entry_status)

        for name_a, name_b in OCS_BULK_CROSS_CONNECTS:
            assert npu.get(ports[name_a], ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == \
                "SAI_OCS_PORT_STATUS_BLOCKED"
            assert npu.get(ports[name_b], ["SAI_OCS_PORT_ATTR_OPER_STATUS"]).value() == \
                "SAI_OCS_PORT_STATUS_BLOCKED"


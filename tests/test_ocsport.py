
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


class TestOcsPort:

    @pytest.fixture(scope="class")
    def created_ocs_ports(self):
        return []

    @pytest.mark.parametrize(
        "name, state",
        OCS_PORTS,
        ids=[
            f"{name}-{state.replace('SAI_OCS_PORT_OVERRIDE_STATE_', '')}"
            for name, state in OCS_PORTS
        ],
    )
    def test_ocs_port_create(self, npu, created_ocs_ports, name, state):
        oid = npu.create(
            SaiObjType.OCS_PORT,
            [
                "SAI_OCS_PORT_ATTR_NAME",
                encode_u8_list(name),
                "SAI_OCS_PORT_ATTR_OVERRIDE_STATE",
                state,
            ],
        )

        assert oid != "oid:0x0"

        created_ocs_ports.append((oid, name))

    @pytest.mark.parametrize(
        "attr, value",
        OCS_PORT_ATTRIBUTES,
        ids=[
            attr.replace("SAI_OCS_PORT_ATTR_", "")
            for attr, _ in OCS_PORT_ATTRIBUTES
        ],
    )
    def test_ocs_port_attr(self, npu, created_ocs_ports, attr, value):
        for oid, name in created_ocs_ports:
            print(f"\nTesting port={name}, attribute={attr}, value={value}")

            npu.set(oid, [attr, value])

            result = npu.get(oid, [attr])

            assert result.value() == value

    def test_ocs_port_remove(self, npu, created_ocs_ports):
        for oid, name in created_ocs_ports:
            npu.remove(oid)

        created_ocs_ports.clear()
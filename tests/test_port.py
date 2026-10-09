import os
import pytest
from pytest_dependency import depends
from saichallenger.common.sai_npu import SaiNpu


def pytest_generate_tests(metafunc):
    if "port_name" not in metafunc.fixturenames or "breakout_mode" not in metafunc.fixturenames:
        return
    testbed = metafunc.config.getoption("--testbed")
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    ports = SaiNpu.get_port_breakout_modes(base_dir=base_dir, testbed=testbed)
    pairs = [(name, mode) for name in sorted(ports) for mode in sorted(ports[name]["modes"])]
    metafunc.parametrize("port_name,breakout_mode", pairs, ids=[f"{p}-{m}" for p, m in pairs])


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))


@pytest.fixture(scope="module", autouse=True)
def skip_saivs(npu):
    if npu is not None and npu.target == "saivs":
        pytest.skip('not supported for "{}" target'.format(npu.target))


@pytest.fixture(scope="module", autouse=True)
def restore_ports(npu):
    yield
    npu.reset()


def _resolve_breakout_ports(npu, cases):
    """Map each breakout case to its port OID by matching HW lane lists cleanly."""
    resolved = []
    for case in cases:
        target_lanes = set(case["lanes"].split(","))
        matched_oid = None
        for oid in npu.port_oids:
            status, data = npu.get(oid, ["SAI_PORT_ATTR_HW_LANE_LIST", npu.make_list(8, "0")], do_assert=False)
            if status == "SAI_STATUS_SUCCESS" and set(data.to_list()) == target_lanes:
                matched_oid = oid
                break
        assert matched_oid is not None, (
            f"no port OID found for alias {case['alias']} with lanes {case['lanes']}"
        )
        resolved.append((matched_oid, case))
    return resolved

class TestDynamicPortBreakout:
    """Port create and attribute checks driven by platform.json breakout modes."""

    @pytest.mark.dependency()
    def test_dynamic_port_breakout(self, npu, port_name, breakout_mode):
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        created = npu.rebreak_port(cases, autoneg="off", fec="none")

        assert len(created) == len(cases)

        for port_oid, case in zip(created, cases):
            expected_speeds = set(case["supported_speeds_mbps"])
            supported = npu.get(port_oid, ["SAI_PORT_ATTR_SUPPORTED_SPEED", npu.make_list(10, "0")]).to_list()
            actual_speeds = {int(s) for s in supported if int(s) != 0}
            assert expected_speeds <= actual_speeds, (
                f"alias {case['alias']} mode {case['mode']}: "
                f"platform {expected_speeds} not in supported {actual_speeds}"
            )

    @pytest.mark.dependency()
    def test_port_admin_state(self, request, npu, port_name, breakout_mode):
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        for port_oid, _case in _resolve_breakout_ports(npu, cases):
            for value in ("true", "false", "true"):
                npu.set(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE", value])
                assert npu.get(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE"]).value() == value

    @pytest.mark.dependency()
    def test_speed_and_fec_change(self, request, npu, port_name, breakout_mode, subtests):
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        for port_oid, case in _resolve_breakout_ports(npu, cases):
            for speed_mbps in case["supported_speeds_mbps"]:
                with subtests.test(port_alias=case["alias"], speed=speed_mbps):
                    npu.set(port_oid, ["SAI_PORT_ATTR_SPEED", str(speed_mbps)])
                    assert npu.get(port_oid, ["SAI_PORT_ATTR_SPEED"]).uint32() == speed_mbps

                    raw_fec = npu.get(port_oid, ["SAI_PORT_ATTR_SUPPORTED_FEC_MODE", npu.make_list(10, "0")]).to_list()
                    fec_modes = [m for m in raw_fec if m and m != "0"] or ["SAI_PORT_FEC_MODE_NONE"]
                    for fec in fec_modes:
                        with subtests.test(port_alias=case["alias"], speed=speed_mbps, fec=fec):
                            npu.set(port_oid, ["SAI_PORT_ATTR_FEC_MODE", fec])
                            assert npu.get(port_oid, ["SAI_PORT_ATTR_FEC_MODE"]).value() == fec

    @pytest.mark.dependency()
    def test_port_loopback_modes(self, request, npu, port_name, breakout_mode, subtests):
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        for port_oid, case in _resolve_breakout_ports(npu, cases):
            lb_modes = [
            "SAI_PORT_INTERNAL_LOOPBACK_MODE_NONE",
            "SAI_PORT_INTERNAL_LOOPBACK_MODE_PHY",
            "SAI_PORT_INTERNAL_LOOPBACK_MODE_MAC"
        ]
            for lb_mode in lb_modes:
                with subtests.test(port_alias=case["alias"], loopback=lb_mode):
                    npu.set(port_oid, ["SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE", lb_mode])
                    assert npu.get(port_oid, ["SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE"]).value() == lb_mode

                    for speed_mbps in case["supported_speeds_mbps"]:
                        with subtests.test(port_alias=case["alias"], loopback=lb_mode, speed=speed_mbps):
                            npu.set(port_oid, ["SAI_PORT_ATTR_SPEED", str(speed_mbps)])
                            assert npu.get(port_oid, ["SAI_PORT_ATTR_SPEED"]).uint32() == speed_mbps

            npu.set(port_oid, ["SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE", "SAI_PORT_INTERNAL_LOOPBACK_MODE_NONE"])
            assert npu.get(port_oid, ["SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE"]).value() == (
                "SAI_PORT_INTERNAL_LOOPBACK_MODE_NONE"
            )
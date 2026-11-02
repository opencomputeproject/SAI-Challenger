import os
import pytest
from pytest_dependency import depends
from saichallenger.common.sai_npu import SaiNpu


def pytest_generate_tests(metafunc):
    if "case" not in metafunc.fixturenames:
        return
    testbed = metafunc.config.getoption("--testbed")
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    ports = SaiNpu.get_port_breakout_modes(base_dir=base_dir, testbed=testbed)

    pairs = []
    for name in ports:
        p_data = ports[name]
        port_obj = {"name": name, "lanes": p_data["lanes"]}
        for mode in sorted(p_data["modes"]):
            pairs.append((port_obj, mode))
    metafunc.parametrize(
        "case",
        pairs,
        ids=[f"{p['name']}-{m}" for p, m in pairs],
        scope="class",
    )


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))


original_port_cache = {}


@pytest.fixture(scope="module", autouse=True)
def restore_ports(npu):
    yield
    original_port_cache.clear()
    npu.reset()


def port_caching(npu, port, autoneg, fec):
    """Snapshot initial state of the platform port into cache if not already done."""
    port_name = port["name"]
    if port_name in original_port_cache:
        return

    parent_lanes = set(port["lanes"].split(","))
    cached_specs = []
    
    for oid in npu.port_oids:
        status, data = npu.get(oid, ["SAI_PORT_ATTR_HW_LANE_LIST", npu.make_list(8, "0")], do_assert=False)
        lanes_list = data.to_list() if status == "SAI_STATUS_SUCCESS" and data else []
        
        if set(lanes_list) & parent_lanes:
            cached_specs.append({
                "lanes": ",".join(lanes_list),
                "speed": str(npu.get(oid, ["SAI_PORT_ATTR_SPEED"]).uint32()),
                "autoneg": autoneg,
                "fec": fec,
            })
    
    assert cached_specs, (
    f"No original port state cached for {port_name}; "
    "cannot perform breakout safely"
    )
            
    original_port_cache[port_name] = cached_specs


def rebreak_port(npu, port, cases):
    """Replace ports on the breakout lanes with the logical ports in cases."""
    port_caching(npu, port, autoneg="off", fec="none")

    specs = [
        {
            "lanes": str(case["lanes"]),
            "speed": str(case.get("speed_mbps", case.get("speed", "100000"))),
            "autoneg": "off",
            "fec": "none",
        }
        for case in cases
    ]
    return npu._replace_ports(specs)


def restore_port(npu, port):
    """Remove current ports on the platform lanes and recreate the cached original ports."""
    cached = original_port_cache[port["name"]]
    
    return npu._replace_ports(cached)

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
    def test_dynamic_port_breakout(self, npu, case):
        port, breakout_mode = case
        port_name = port["name"]
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        created = rebreak_port(npu, port, cases)
        assert len(created) == len(cases)

    @pytest.mark.dependency()
    def test_supported_speed(self, request, npu, case, subtests):
        port, breakout_mode = case
        port_name = port["name"]
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu,port_name=port_name,breakout_mode=breakout_mode)
        resolved_ports = _resolve_breakout_ports(npu, cases)
        status, data = npu.get(resolved_ports[0][0], ["SAI_PORT_ATTR_SUPPORTED_SPEED", npu.make_list(10, "0")], do_assert=False)
        if status == "SAI_STATUS_NOT_IMPLEMENTED":
            pytest.skip("SAI_PORT_ATTR_SUPPORTED_SPEED is not implemented")
        assert status == "SAI_STATUS_SUCCESS", (f"Failed to get supported speeds: {status}")

        for port_oid, case in resolved_ports:
            with subtests.test(port=case["alias"], expected_speeds=case["supported_speeds_mbps"]):
                expected_speeds = set(case["supported_speeds_mbps"])
                status, data = npu.get(port_oid, ["SAI_PORT_ATTR_SUPPORTED_SPEED", npu.make_list(10, "0")], do_assert=False)
                supported = data.to_list()

                actual_speeds = {int(s) for s in supported if int(s) != 0}
                assert expected_speeds <= actual_speeds, (
                    f"alias {case['alias']} mode {case['mode']}: "
                    f"platform {expected_speeds} not in supported {actual_speeds}"
                )

    @pytest.mark.dependency()
    def test_port_admin_state(self, request, npu, case, subtests):
        port, breakout_mode = case
        port_name = port["name"]
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        for port_oid, case in _resolve_breakout_ports(npu, cases):
            for value in ("true", "false", "true"):
                with subtests.test(port_alias=case["alias"], admin_state=value):
                    npu.set(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE", value])
                    assert npu.get(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE"]).value() == value

    @pytest.mark.dependency()
    def test_speed_and_fec_change(self, request, npu, case, subtests):
        port, breakout_mode = case
        port_name = port["name"]
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        resolved_ports = _resolve_breakout_ports(npu, cases)

        status, data = npu.get(resolved_ports[0][0], ["SAI_PORT_ATTR_SUPPORTED_FEC_MODE", npu.make_list(10, "0")], do_assert=False)
        if status == "SAI_STATUS_NOT_IMPLEMENTED":
            pytest.skip("SAI_PORT_ATTR_SUPPORTED_FEC_MODE is not implemented")
        assert status == "SAI_STATUS_SUCCESS", (f"Failed to get supported FEC modes: {status}")

        for port_oid, case in resolved_ports:
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
    def test_port_loopback_modes(self, request, npu, case, subtests):
        port, breakout_mode = case
        port_name = port["name"]
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

    @pytest.mark.dependency()
    def test_port_recovery(self, request, npu, case):
        port, breakout_mode = case
        port_name = port["name"]
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        restored = restore_port(npu, port)
        cached = original_port_cache[port_name]

        assert len(restored) == len(cached)
        for port_oid, spec in zip(restored, cached):
            status, data = npu.get(port_oid, ["SAI_PORT_ATTR_HW_LANE_LIST", npu.make_list(8, "0")], do_assert=False)
            actual_lanes = data.to_list() if status == "SAI_STATUS_SUCCESS" and data else []
            assert set(actual_lanes) == set(spec["lanes"].split(","))
            assert npu.get(port_oid, ["SAI_PORT_ATTR_SPEED"]).uint32() == int(spec["speed"])
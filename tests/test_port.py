import os
import pytest
from pytest_dependency import depends
from saichallenger.common.sai_npu import SaiNpu


def pytest_generate_tests(metafunc):
    if "port" not in metafunc.fixturenames or "breakout_mode" not in metafunc.fixturenames:
        return
    testbed = metafunc.config.getoption("--testbed")
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    ports = SaiNpu.get_port_breakout_modes(base_dir=base_dir, testbed=testbed)

    pairs = []
    for name in sorted(ports):
        p_data = ports[name]
        port_obj = {"name": name, "lanes": p_data["lanes"]}
        for mode in sorted(p_data["modes"]):
            pairs.append((port_obj, mode))
    metafunc.parametrize("port,breakout_mode", pairs, ids=[f"{p['name']}-{m}" for p, m in pairs], scope="class")


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))


@pytest.fixture(scope="module", autouse=True)
def skip_saivs(npu):
    if npu is not None and npu.target == "saivs":
        pytest.skip('not supported for "{}" target'.format(npu.target))


original_port_cache = {}


@pytest.fixture(scope="module", autouse=True)
def restore_ports(npu):
    yield
    original_port_cache.clear()
    npu.reset()


def port_caching(npu, port):
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
            fec_val = npu.get(oid, ["SAI_PORT_ATTR_FEC_MODE"]).value()
            if fec_val.startswith("SAI_PORT_FEC_MODE_"):
                fec_val = fec_val[len("SAI_PORT_FEC_MODE_"):].lower()
                
            autoneg_val = npu.get(oid, ["SAI_PORT_ATTR_AUTO_NEG_MODE"]).value()
            
            cached_specs.append({
                "lanes": ",".join(lanes_list),
                "speed": str(npu.get(oid, ["SAI_PORT_ATTR_SPEED"]).uint32()),
                "autoneg": "on" if autoneg_val == "true" else "off",
                "fec": fec_val,
            })
            
    original_port_cache[port_name] = cached_specs


def rebreak_port(npu, port, cases, autoneg="off", fec="none"):
    """Replace ports on the breakout lanes with the logical ports in cases."""
    port_caching(npu, port)

    specs = [
        {
            "lanes": str(case["lanes"]),
            "speed": str(case.get("speed_mbps", case.get("speed", "100000"))),
            "autoneg": autoneg,
            "fec": fec,
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
    def test_dynamic_port_breakout(self, npu, port, breakout_mode):
        port_name = port["name"]
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        created = rebreak_port(npu, port, cases, autoneg="off", fec="none")
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
    def test_port_admin_state(self, request, npu, port, breakout_mode):
        port_name = port["name"]
        depends(request, [f"TestDynamicPortBreakout::test_dynamic_port_breakout[{port_name}-{breakout_mode}]"])
        cases = SaiNpu.get_port_breakout_modes(npu=npu, port_name=port_name, breakout_mode=breakout_mode)
        for port_oid, _case in _resolve_breakout_ports(npu, cases):
            for value in ("true", "false", "true"):
                npu.set(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE", value])
                assert npu.get(port_oid, ["SAI_PORT_ATTR_ADMIN_STATE"]).value() == value

    @pytest.mark.dependency()
    def test_speed_and_fec_change(self, request, npu, port, breakout_mode, subtests):
        port_name = port["name"]
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
    def test_port_loopback_modes(self, request, npu, port, breakout_mode, subtests):
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
    def test_port_recovery(self, request, npu, port, breakout_mode):
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
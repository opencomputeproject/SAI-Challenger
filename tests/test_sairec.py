import pytest
import time

@pytest.fixture(scope="module")
def bcm56850_teardown(npu):
    yield
    if npu.name == "BCM56850":
        npu.reset()


@pytest.fixture(scope="module")
def tofino_teardown(npu):
    yield
    if npu.name == "tofino":
        npu.reset()


@pytest.mark.parametrize(
    "fname",
    [
        #"BCM56850/full.rec",
        "BCM56850/empty_sw.rec",
        "BCM56850/bridge_create_1.rec",
        "BCM56850/hostif.rec",
        "BCM56850/acl_tables.rec",
        "BCM56850/bulk_fdb.rec",
        "BCM56850/bulk_route.rec",
        #"BCM56850/tunnel_map.rec",
        "BCM56850/remove_create_port.rec"
    ],
)
def test_apply_sairec(npu, exec_params, dataplane, fname, bcm56850_teardown):
    if npu.name != "BCM56850":
        pytest.skip("VS specific scenario")

    if exec_params["server"] != 'localhost':
        pytest.skip("Currently not supported in client-server mode")

    npu.apply_rec("/sai/sonic-sairedis/tests/" + fname)


@pytest.mark.parametrize(
    "fname",
    [
        "t0_full.rec",
        "t1_full.rec",
        "t1_lag_full.rec",
    ],
)
def test_tofino_scenario(npu, dataplane, fname, tofino_teardown):
    if npu.name != 'tofino':
        pytest.skip("Tofino specific scenario")

    npu.apply_rec(f"/sai-challenger/npu/intel/{npu.name}/{npu.target}/scenarios/{fname}")

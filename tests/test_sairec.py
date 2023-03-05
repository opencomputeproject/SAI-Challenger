import pytest
import time


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.meta.name))


@pytest.fixture(scope="module")
def bcm56850_teardown(npu):
    yield
    if npu.name in ["BCM56850", "trident2"]:
        npu.reset()


@pytest.fixture(scope="module")
def trident3_teardown(npu):
    yield
    if npu.name in ["trident3"]:
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
def test_apply_sairec(npu, dataplane, fname, bcm56850_teardown):
    if npu.name not in ["BCM56850", "trident2"]:
        pytest.skip("VS specific scenario")

    if npu.sai_client.config["ip"] != 'localhost':
        pytest.skip("Currently not supported in client-server mode")

    npu.apply_rec("/sai/sonic-sairedis/tests/" + fname)


@pytest.mark.parametrize(
    "fname",
    [
        "t1_factory_default.rec",
    ],
)
def test_trident3_scenario(npu, dataplane, fname, trident3_teardown):
    if npu.name != "trident3":
        pytest.skip("Trident3 specific scenario")

    npu.apply_rec(f"/sai-challenger/npu/broadcom/{npu.name}/{npu.target}/scenarios/{fname}")


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

import pytest


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
def test_apply_sairec(sai, sai_server, dataplane, fname):
    if sai_server != 'localhost':
        pytest.skip("Currently not supported in client-server mode")
    sai.apply_rec("/sai/sonic-sairedis/tests/" + fname)
    sai.cleanup()

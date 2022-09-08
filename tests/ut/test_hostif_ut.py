import pytest
from sai_data import SaiObjType
from ptf.testutils import simple_tcp_packet, send_packet, verify_packets


@pytest.fixture(scope="module")
def sai_hostif_obj(npu):
    hostif_oid = npu.create(SaiObjType.HOSTIF,
                            [
                                "SAI_HOSTIF_ATTR_TYPE",        "SAI_HOSTIF_TYPE_NETDEV",
                                "SAI_HOSTIF_ATTR_NAME",        "Ethernet0",
                                "SAI_HOSTIF_ATTR_OBJ_ID",      npu.port_oids[0],
                                "SAI_HOSTIF_ATTR_OPER_STATUS", "true"
                            ])
    if npu.libsaivs:
        # BUG: After hostif creation on saivs, both created netdev
        #      and related FP port are in admin down state.
        npu.remote_iface_status_set("eth1", True)
        npu.remote_iface_status_set("Ethernet0", True)
    return hostif_oid


@pytest.fixture(scope="function")
def hostif_dataplane(npu):
    hostifs = {
        "100": "Ethernet0"
    }
    hostif_dataplane = npu.hostif_dataplane_start(hostifs)
    yield hostif_dataplane
    npu.hostif_dataplane_stop()


@pytest.mark.dependency()
def test_netdev_create(npu, sai_hostif_obj):
    assert npu.remote_iface_exists("Ethernet0") == True


@pytest.mark.dependency(depends=['test_netdev_create'])
def test_netdev_pkt(npu, dataplane, sai_hostif_obj, hostif_dataplane):
    if not npu.libsaivs:
        pytest.skip("valid for saivs only")

    assert hostif_dataplane is not None

    pkt = simple_tcp_packet(eth_dst='00:00:00:11:11:11',
                            eth_src='00:00:00:22:22:22',
                            ip_dst='10.0.0.1',
                            ip_id=102,
                            ip_ttl=64)

    send_packet(dataplane, 0, pkt)

    npu.hostif_pkt_listen()
    verify_packets(hostif_dataplane, pkt, [100])


@pytest.mark.dependency(depends=['test_netdev_create'])
def test_netdev_remove(npu, sai_hostif_obj):
    npu.remove(sai_hostif_obj)
    assert npu.remote_iface_exists("Ethernet0") == False

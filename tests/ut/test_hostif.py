import pytest
from sai import SaiObjType


@pytest.fixture(scope="module")
def sai_hostif_obj(npu):
    hostif_oid = npu.create(SaiObjType.HOSTIF,
                            [
                                "SAI_HOSTIF_ATTR_TYPE",    "SAI_HOSTIF_TYPE_NETDEV",
                                "SAI_HOSTIF_ATTR_NAME",    "Ethernet0",
                                "SAI_HOSTIF_ATTR_OBJ_ID",  npu.port_oids[0]
                            ])
    return hostif_oid


def test_netdev_create(npu, sai_hostif_obj):
    assert npu.remote_iface_exists("Ethernet0") == True
    assert npu.remote_iface_exists("Ethernet4") == False


def test_netdev_remove(npu, sai_hostif_obj):
    npu.remove(sai_hostif_obj)
    assert npu.remote_iface_exists("Ethernet0") == False

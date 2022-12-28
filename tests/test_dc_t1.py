import pytest
from sai_data import SaiObjType
import topologies.dc_t1


@pytest.fixture(scope="module")
def dc_t1_topology(npu):
    with topologies.dc_t1.config(npu) as result:
        yield result


def test_basic_route(npu, dc_t1_topology):
    npu.create_route("100.0.0.0/8", npu.default_vrf_oid, dc_t1_topology["cpu_port_oid"],
                     ["SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION", "SAI_PACKET_ACTION_FORWARD"])

    npu.remove_route("100.0.0.0/8", npu.default_vrf_oid)


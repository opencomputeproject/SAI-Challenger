import pytest
from saichallenger.common.sai_data import SaiObjType
from sai_client.sai_redis_client.sai_redis_client import SaiRedisClient

from ptf.testutils import simple_tcp_packet, send_packet, verify_packets


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance, npu):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

    if not isinstance(npu.sai_client, SaiRedisClient):
        pytest.skip("Warm boot logic is not implemented for non-redis SAI client")

@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()

def test_warmboot(npu, dataplane):
    """
    Description:
    Check warm boot functionality

    Test scenario:
    1. Create a VLAN 10
    2. Add two ports as untagged members to the VLAN
    3. Setup static FDB entries for port 1 and port 2
    4. Perform warm boot
    4. Send a simple untagged packet on port 1 and verify packet on port 2
    5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 2
    vlan_mbr_oids = []

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(max_port):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        vlan_mbr = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
        npu.create_fdb(vlan_oid, macs[idx], npu.dot1q_bp_oids[idx])

    npu.perform_warm_reboot()

    if npu.run_traffic:
        pkt = simple_tcp_packet(eth_dst=macs[1],
                                eth_src=macs[0],
                                ip_dst='10.0.0.1',
                                ip_id=101,
                                ip_ttl=64)

        send_packet(dataplane, 0, pkt)
        verify_packets(dataplane, pkt, [1])

    for idx in range(max_port):
        npu.remove_fdb(vlan_oid, macs[idx])
        npu.remove(vlan_mbr_oids[idx])
        npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

    npu.remove(vlan_oid)

def test_two_warmboots(npu, dataplane):
    """
    Description:
    Check two warm boot functionality

    Test scenario:
    1. Create a VLAN 10
    2. Add two ports as untagged members to the VLAN
    3. Setup static FDB entries for port 1 and port 2
    4. Perform warm boot, verify forwarding, repeat once
    5. Clean up configuration
    """
    vlan_id = "10"
    macs = ['00:11:11:11:11:11', '00:22:22:22:22:22']
    max_port = 2
    vlan_mbr_oids = []

    vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])

    for idx in range(max_port):
        npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx])
        vlan_mbr = npu.create_vlan_member(vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        vlan_mbr_oids.append(vlan_mbr)
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", vlan_id])
        npu.create_fdb(vlan_oid, macs[idx], npu.dot1q_bp_oids[idx])

    pkt = simple_tcp_packet(eth_dst=macs[1],
                            eth_src=macs[0],
                            ip_dst='10.0.0.1',
                            ip_id=101,
                            ip_ttl=64)

    for _ in range(2):
        npu.perform_warm_reboot()
        if npu.run_traffic:
            send_packet(dataplane, 0, pkt)
            verify_packets(dataplane, pkt, [1])

    for idx in range(max_port):
        npu.remove_fdb(vlan_oid, macs[idx])
        npu.remove(vlan_mbr_oids[idx])
        npu.create_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[idx], "SAI_VLAN_TAGGING_MODE_UNTAGGED")
        npu.set(npu.port_oids[idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])

    npu.remove(vlan_oid)
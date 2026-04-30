import ipaddress
import pytest
import time
from saichallenger.common.sai_data import SaiObjType
from ptf.testutils import simple_tcp_packet, send_packet, verify_packets, verify_packet, verify_no_packet_any, verify_no_packet, verify_any_packet_any_port
from sai_client.sai_redis_client.sai_redis_client import SaiRedisClient



@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

def test_simple_port_counters(npu):
    """
    Description:
    Check if we can set counter polling and verify counters
    """
    if isinstance(npu.sai_client, SaiRedisClient):
        group_name = "PORT_STAT_COUNTER"
        counters = ["SAI_PORT_STAT_IF_IN_UCAST_PKTS","SAI_PORT_STAT_IF_OUT_UCAST_PKTS"]
        # ms
        poll_interval = 100
        # enable counter poll
        redis_client = npu.sai_client

        # enable counter polling for group
        redis_client.set_counter_group(group_name,
                                          ["POLL_INTERVAL", poll_interval, "STATS_MODE", "STATS_MODE_READ", "FLEX_COUNTER_STATUS", "enable"])
        redis_client.start_counter_poll(group_name + ':' + npu.port_oids[0],
                                          ["PORT_COUNTER_ID_LIST", ",".join(counters)])

        # do some work, e. g. send traffic
        # wait for poll_intervall * 2 to be sure that polling has happened
        time.sleep(2 * poll_interval / 1000)

        # get value for counter
        exists, data = redis_client.get_counter(npu.port_oids[0], counters)
        try:
            assert(exists)
            assert(data[counters[0]] == '0')
            assert(data[counters[1]] == '0')
        finally:
            # disable counter polling for group
            redis_client.set_counter_group(group_name,
                                            ["FLEX_COUNTER_STATUS", "enable"])
            # delete counter group and counter 
            redis_client.stop_counter_poll(group_name + ':' + npu.port_oids[0], [])
            redis_client.del_counter_group(group_name, [])

            # delete counter from COUNTER_DB
            redis_client.del_counter(npu.port_oids[0])

    else:
        assert(False)
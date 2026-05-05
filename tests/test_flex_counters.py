import pytest
import time
from sai_client.sai_redis_client.sai_redis_client import SaiRedisClient


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

def test_port_counters(npu):
    """
    Description:
    Check if we can set counter polling and verify counters
    """
    if isinstance(npu.sai_client, SaiRedisClient):
        group_name = "PORT_COUNTER_GROUP"
        counters = ["SAI_PORT_STAT_IF_IN_UCAST_PKTS","SAI_PORT_STAT_IF_OUT_UCAST_PKTS"]
        poll_interval_ms = 100

        npu.set_counter_group(group_name=group_name,
                              enable=True,
                              poll_interval=poll_interval_ms,
                              clear_on_read=False)
        npu.start_counter_poll(group_name=group_name,
                               oid=npu.port_oids[0],
                               counter_type="Port Counter",
                               counters=counters)
        
        # do some work, e. g. send traffic

        # wait for poll_interval * 2 to be sure that polling has happened
        time.sleep(2 * poll_interval_ms / 1000)

        exists, data = npu.get_counter(oid=npu.port_oids[0], counters=counters)
        try:
            assert(exists)
            assert(data[counters[0]] == '0')
            assert(data[counters[1]] == '0')
        finally:
            # stop counter polling and delete counters from FLEX_COUNTER_DB and COUNTERS_DB
            npu.stop_counter_poll(group_name=group_name,
                                  oid=npu.port_oids[0])
            npu.del_counter_group(group_name)
            npu.del_counter(npu.port_oids[0])
    else:
        pytest.skip("Flex counters are supported only for redis SAI client")
import pytest
import time
from sai_client.sai_redis_client.sai_redis_client import SaiRedisClient
from saichallenger.common.sai_constants import DEFAULT_POLL_INTERVAL_MS

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
    if not isinstance(npu.sai_client, SaiRedisClient):
        pytest.skip("Flex counters are supported only for redis SAI client")

    group_name = "PORT_COUNTER_GROUP"
    counters = ["SAI_PORT_STAT_IF_IN_UCAST_PKTS","SAI_PORT_STAT_IF_OUT_UCAST_PKTS"]

    npu.set_counter_group(group_name)
    npu.start_counter_poll(group_name, npu.port_oids[0], counters)
    
    # do some work, e. g. send traffic

    # wait for poll_interval * 2 to be sure that polling has happened
    time.sleep(2 * DEFAULT_POLL_INTERVAL_MS / 1000)

    exists, data = npu.get_counter(npu.port_oids[0], counters)
    try:
        assert(exists)
        assert(data[counters[0]] == '0')
        assert(data[counters[1]] == '0')
    finally:
        # stop counter polling and delete counters from FLEX_COUNTER_DB and COUNTERS_DB
        npu.stop_counter_poll(group_name, npu.port_oids[0])
        npu.del_counter_group(group_name)
        npu.del_counter(npu.port_oids[0])


def test_multiple_counter_types(npu):
    """
    Description:
    Check if we can set counter polling for multiple counter types
    """
    if not isinstance(npu.sai_client, SaiRedisClient):
        pytest.skip("Flex counters are supported only for redis SAI client")

    port_group_name = "PORT_COUNTER_GROUP"
    port_debug_group_name = "PORT_DEBUG_COUNTER_GROUP"
    queue_group_name = "QUEUE_COUNTER_GROUP"
    queue_attr_group_name = "QUEUE_ATTR_GROUP"

    port_counters = ["SAI_PORT_STAT_IF_IN_UCAST_PKTS","SAI_PORT_STAT_IF_OUT_UCAST_PKTS"]
    port_debug_counters = ["SAI_PORT_STAT_IF_IN_UCAST_PKTS","SAI_PORT_STAT_IF_IN_OCTETS"]
    queue_counters = ["SAI_QUEUE_STAT_PACKETS","SAI_QUEUE_STAT_BYTES"]
    queue_attr_counters = ["SAI_QUEUE_ATTR_PORT","SAI_QUEUE_ATTR_INDEX","SAI_QUEUE_ATTR_TYPE"]

    # we could have used single group for all counters as they have same configs, but
    # we create separate groups in order to generate more syncd threads
    npu.set_counter_group(port_group_name)
    npu.set_counter_group(port_debug_group_name)
    npu.set_counter_group(queue_group_name)
    npu.set_counter_group(queue_attr_group_name)


    npu.start_counter_poll(port_group_name, npu.port_oids[0], port_counters)
    # ordinary port counters and debug port counters are the same object in syncd but 
    # with different flags, which affects which SAI API is used to get the counters
    npu.start_counter_poll(port_debug_group_name, npu.port_oids[0], port_debug_counters, counter_type="Port Debug Counter")

    queue_oids = npu.get_list(npu.port_oids[0], "SAI_PORT_ATTR_QOS_QUEUE_LIST", "oid:0x0")
    assert len(queue_oids) > 0
    npu.start_counter_poll(queue_group_name, queue_oids[0], queue_counters)
    npu.start_counter_poll(queue_attr_group_name, queue_oids[0], queue_attr_counters)
    
    # do some work, e. g. send traffic

    time.sleep(2 * DEFAULT_POLL_INTERVAL_MS / 1000)

    exists_port, data_port = npu.get_counter(npu.port_oids[0], port_counters)
    exists_port_debug, data_port_debug = npu.get_counter(npu.port_oids[0], port_debug_counters)
    exists_queue, data_queue = npu.get_counter(queue_oids[0], queue_counters)
    exists_queue_attr, data_queue_attr = npu.get_counter(queue_oids[0], queue_attr_counters)
    try:
        assert(exists_port)
        assert(data_port[port_counters[0]] == '0')
        assert(data_port[port_counters[1]] == '0')

        assert(exists_port_debug)
        assert(data_port_debug[port_debug_counters[0]] == '0')
        assert(data_port_debug[port_debug_counters[1]] == '0')

        assert(exists_queue)
        assert(data_queue[queue_counters[0]] == '0')
        assert(data_queue[queue_counters[1]] == '0')

        assert(exists_queue_attr)
        port_rid = npu.sai_client.vid_to_rid(npu.port_oids[0])
        assert(data_queue_attr[queue_attr_counters[0]] == port_rid)
        assert(data_queue_attr[queue_attr_counters[1]] == '0')
        assert(data_queue_attr[queue_attr_counters[2]] == 'SAI_QUEUE_TYPE_UNICAST')
    finally:
        # stop counter polling and delete counters from FLEX_COUNTER_DB and COUNTERS_DB
        npu.stop_counter_poll(port_group_name,npu.port_oids[0])
        npu.stop_counter_poll(port_debug_group_name, npu.port_oids[0])
        npu.stop_counter_poll(queue_group_name, queue_oids[0])
        npu.stop_counter_poll(queue_attr_group_name, queue_oids[0])

        npu.del_counter_group(port_group_name)
        npu.del_counter_group(port_debug_group_name)
        npu.del_counter_group(queue_group_name)
        npu.del_counter_group(queue_attr_group_name)

        npu.del_counter(npu.port_oids[0])
        npu.del_counter(queue_oids[0])
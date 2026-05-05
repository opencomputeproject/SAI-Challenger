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


def test_multiple_counter_types(npu):
    """
    Description:
    Check if we can set counter polling for multiple counter types
    """
    if isinstance(npu.sai_client, SaiRedisClient):
        port_group_name = "PORT_COUNTER_GROUP"
        queue_group_name = "QUEUE_COUNTER_GROUP"
        queue_attr_group_name = "QUEUE_ATTR_GROUP"
        port_counters = ["SAI_PORT_STAT_IF_IN_UCAST_PKTS","SAI_PORT_STAT_IF_OUT_UCAST_PKTS"]
        queue_counters = ["SAI_QUEUE_STAT_PACKETS","SAI_QUEUE_STAT_BYTES"]
        queue_attr_counters = ["SAI_QUEUE_ATTR_PORT","SAI_QUEUE_ATTR_INDEX","SAI_QUEUE_ATTR_TYPE"]
        poll_interval_ms = 100

        # we could have used single group for all counters as they have same configs, but
        # we create separate groups in order to generate more syncd threads
        npu.set_counter_group(group_name=port_group_name,
                              enable=True,
                              poll_interval=poll_interval_ms,
                              clear_on_read=False)
        npu.set_counter_group(group_name=queue_group_name,
                              enable=True,
                              poll_interval=poll_interval_ms,
                              clear_on_read=False)
        npu.set_counter_group(group_name=queue_attr_group_name,
                              enable=True,
                              poll_interval=poll_interval_ms,
                              clear_on_read=False)
        
        npu.start_counter_poll(group_name=port_group_name,
                               oid=npu.port_oids[0],
                               counter_type="Port Counter",
                               counters=port_counters)
        queue_oids = npu.get_list(npu.port_oids[0], "SAI_PORT_ATTR_QOS_QUEUE_LIST", "oid:0x0")
        assert len(queue_oids) > 0
        npu.start_counter_poll(group_name=queue_group_name,
                    oid=queue_oids[0],
                    counter_type="Queue Counter",
                    counters=queue_counters)
        npu.start_counter_poll(group_name=queue_attr_group_name,
                    oid=queue_oids[0],
                    counter_type="Queue Attribute",
                    counters=queue_attr_counters)
        
        # do some work, e. g. send traffic

        time.sleep(2 * poll_interval_ms / 1000)

        exists_port, data_port = npu.get_counter(oid=npu.port_oids[0], counters=port_counters)
        exists_queue, data_queue = npu.get_counter(oid=queue_oids[0], counters=queue_counters)
        exists_queue_attr, data_queue_attr = npu.get_counter(oid=queue_oids[0], counters=queue_attr_counters)
        
        try:
            assert(exists_port)
            assert(data_port[port_counters[0]] == '0')
            assert(data_port[port_counters[1]] == '0')
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
            npu.stop_counter_poll(group_name=port_group_name,
                                  oid=npu.port_oids[0])
            npu.stop_counter_poll(group_name=queue_group_name,
                                  oid=queue_oids[0])
            npu.stop_counter_poll(group_name=queue_attr_group_name,
                                  oid=queue_oids[0])

            npu.del_counter_group(port_group_name)
            npu.del_counter_group(queue_group_name)
            npu.del_counter_group(queue_attr_group_name)

            npu.del_counter(npu.port_oids[0])
            npu.del_counter(queue_oids[0])
    else:
        pytest.skip("Flex counters are supported only for redis SAI client")
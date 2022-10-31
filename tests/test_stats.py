import pytest


def test_stats(npu, dataplane):

    # Get ports list
    port_oids = npu.get_list(npu.switch_oid, "SAI_SWITCH_ATTR_PORT_LIST", "oid:0x0")
    assert len(port_oids) > 0

    # Clear some port stats for port 0
    status = npu.clear_stats(oid=port_oids[0],
                             attrs=[
                                'SAI_PORT_STAT_IF_IN_OCTETS', '',
                                'SAI_PORT_STAT_IF_IN_UCAST_PKTS', '',
                                'SAI_PORT_STAT_IF_OUT_OCTETS', ''
                            ])

    # Get some port stats for port 0
    cntrs = npu.get_stats(oid=port_oids[0],
                          attrs=[
                              'SAI_PORT_STAT_IF_IN_OCTETS', '',
                              'SAI_PORT_STAT_IF_IN_UCAST_PKTS', '',
                              'SAI_PORT_STAT_IF_OUT_OCTETS', ''
                          ]).counters()

    for cntr_id in cntrs:
        assert cntrs[cntr_id] == 0, "{} is not 0".format(cntr_id)

    queue_oids = npu.get_list(port_oids[0], "SAI_PORT_ATTR_QOS_QUEUE_LIST", "oid:0x0")
    assert len(queue_oids) > 0

    # Get queues stats
    for queue_oid in queue_oids:
        cntrs = npu.get_stats(oid=queue_oid,
                              attrs=[
                                  'SAI_QUEUE_STAT_PACKETS', '',
                                  'SAI_QUEUE_STAT_BYTES', ''
                              ]).counters()
        for cntr_id in cntrs:
            assert cntrs[cntr_id] == 0, "{} is not 0".format(cntr_id)


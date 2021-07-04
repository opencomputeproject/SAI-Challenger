import pytest


def test_stats(npu, dataplane):
    # Get ports list
    ports = npu.get("SAI_OBJECT_TYPE_SWITCH:" + npu.oid,
                    ["SAI_SWITCH_ATTR_PORT_LIST", npu.make_list(33, "oid:0x0")])

    port_oids = ports.oids()

    # Clear some port stats for port 0
    status = npu.clear_stats("SAI_OBJECT_TYPE_PORT:" + port_oids[0],
                            [
                                'SAI_PORT_STAT_IF_IN_OCTETS', '',
                                'SAI_PORT_STAT_IF_IN_UCAST_PKTS', '',
                                'SAI_PORT_STAT_IF_OUT_OCTETS', ''
                            ])

    # Get some port stats for port 0
    cntrs = npu.get_stats("SAI_OBJECT_TYPE_PORT:" + port_oids[0],
                          [
                              'SAI_PORT_STAT_IF_IN_OCTETS', '',
                              'SAI_PORT_STAT_IF_IN_UCAST_PKTS', '',
                              'SAI_PORT_STAT_IF_OUT_OCTETS', ''
                          ])
    cntr_list = cntrs.counters()

    for cntr_id in cntr_list:
        assert cntr_list[cntr_id] == 0, "{} is not 0".format(cntr_id)
    






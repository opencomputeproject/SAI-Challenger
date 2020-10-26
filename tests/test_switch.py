import redis
import time
import pytest

def test_switch_create():
    r = redis.Redis(db=1)
    r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", "SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000", '["SAI_SWITCH_ATTR_INIT_SWITCH","true","SAI_SWITCH_ATTR_SRC_MAC_ADDRESS","52:54:00:EE:BB:70"]', "Screate")
    r.publish("ASIC_STATE_CHANNEL", "G")
    time.sleep(0.5)

    assert r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")
    time.sleep(0.5)

    assert len(r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)) == 0

def test_get_switch_attr():
    r = redis.Redis(db=1)
    r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", "SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000", '["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID","oid:0x0"]', "Sget")
    r.publish("ASIC_STATE_CHANNEL", "G")
    time.sleep(0.5)

    assert r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")
    time.sleep(0.5)


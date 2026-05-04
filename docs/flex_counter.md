# Flex counters support

This document describes what are flex counters and what was added for this feature 

### How flex counters are managed in SONiC

Flex counters are SONiC's mechanism for controlling periodic polling of SAI counters and, in some cases, SAI attributes for different classes of switch objects. Data related to flex counters is stored in `FLEX_COUNTER_DB`. Multiple flex counters are grouped in flex counter group. For each group `syncd` creates a separate thread in which it polls stats from SAI and stores them in `COUNTERS_DB`. SONiC CLI tools read counters from `COUNTERS_DB`

Each group has its own configuration entry and can typically be:

1. enabled or disabled
2. assigned a polling interval
3. configured with a stats mode
4. optionally list of plugins (lua script) SHAs
5. optionally tuned with bulk-polling parameters for some groups

Examples of group names:

* PG_DROP_STAT_COUNTER
* PG_WATERMARK_STAT_COUNTER
* PORT_BUFFER_DROP_STAT
* PORT_STAT_COUNTER
* QUEUE_STAT_COUNTER
* RIF_STAT_COUNTER

To see more run the command below or check this [implementation file](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/flexcounterorch.cpp#L68C1-L68C52):
```sh
redis-cli -n 5 --scan | cut -d ':' -f1,2 | sort -u
```

Running configs for flex counter groups are stored in `CONFIG_DB`, based on this data `orchagent` tells `syncd` how to configure flex counter group and which counters it should poll. `Syncd` stores this configuration in `FLEX_COUNTER_DB` e. g.:

`FLEX_COUNTER_GROUP_TABLE:PORT_STAT_COUNTER` - stores configuration for group
`FLEX_COUNTER_TABLE:PORT_STAT_COUNTER:oid` - stores configuration (counters ids) for different SAI objects 

There are 3 ways how `orchagent` and `syncd` communicate with each other:

1. Using `FLEX_COUNTER_GROUP_TABLE_KEY_VALUE_OP_QUEUE` and `FLEX_COUNTER_TABLE_KEY_VALUE_OP_QUEUE` from `FLEX_COUNTER_DB`
2. Using `ASIC_STATE_KEY_VALUE_OP_QUEUE` from `ASIC_DB`
3. Using ZMQ connection

By default SONiC uses either 2nd or 3rd method

Below are examples how to manage flex counters groups and polls using redis-cli:
```sh
# set counter group
redis-cli -n 5 LPUSH FLEX_COUNTER_GROUP_TABLE_KEY_VALUE_OP_QUEUE PORT_STAT_COUNTER '["POLL_INTERVAL","2000","STATS_MODE","STATS_MODE_READ","FLEX_COUNTER_STATUS","enable"]' SSET
redis-cli -n 5 PUBLISH FLEX_COUNTER_GROUP_TABLE_CHANNEL@5 G
# or 
redis-cli -n 1 LPUSH ASIC_STATE_KEY_VALUE_OP_QUEUE PORT_STAT_COUNTER '["POLL_INTERVAL","2000","STATS_MODE","STATS_MODE_READ","FLEX_COUNTER_STATUS","enable"]' Sset_counter_group
redis-cli -n 1 PUBLISH ASIC_STATE_CHANNEL@1 G
# delete flex counter group 
redis-cli -n 1 LPUSH ASIC_STATE_KEY_VALUE_OP_QUEUE PORT_STAT_COUNTER '[]' Ddel_counter_group
redis-cli -n 1 PUBLISH ASIC_STATE_CHANNEL@1 G

# set counter object
redis-cli -n 5 LPUSH FLEX_COUNTER_TABLE_KEY_VALUE_OP_QUEUE PORT_STAT_COUNTER:oid:0x1000000000011 '["PORT_COUNTER_ID_LIST","SAI_PORT_STAT_IF_IN_UCAST_PKTS"]' SSET
redis-cli -n 5 PUBLISH FLEX_COUNTER_TABLE_CHANNEL@5 G
# or 
redis-cli -n 1 LPUSH ASIC_STATE_KEY_VALUE_OP_QUEUE PORT_STAT_COUNTER:oid:0x1000000000011 '["PORT_COUNTER_ID_LIST","SAI_PORT_STAT_IF_IN_UCAST_PKTS"]' Sstart_poll
redis-cli -n 1 PUBLISH ASIC_STATE_CHANNEL@1 G
# stop flex counter polling
redis-cli -n 1 LPUSH ASIC_STATE_KEY_VALUE_OP_QUEUE PORT_STAT_COUNTER:oid:0x1000000000011 '[]' Dstop_poll
redis-cli -n 1 PUBLISH ASIC_STATE_CHANNEL@1 G
```

### How flex counters are managed in SAI-Challenger

Due to the need of `syncd` process, flex counter support will work only for `SaiRedisClient`. The 2nd way of communication (using `ASIC_STATE_KEY_VALUE_OP_QUEUE`) with `syncd` was chosen, as we already do this for SAI object management. For implementation details look at [sai_redis_client.py](../common/sai_client/sai_redis_client/sai_redis_client.py)

### New sai CLI commands

New commands for configuring flex counter group and counter are added:
```sh
sai counter group set <group-name> <attr1> <val1> ...
sai counter group del <group-name> 
sai counter poll start <group-name> <oid> <attr1> <val1> ...
sai counter poll stop <group-name> <oid>
sai counter get <oid> ? <counter-ids1> ...
sai counter del <oid> 
```

With some examples:
```sh
sai counter group set PORT_STAT_COUNTER POLL_INTERVAL 2000 STATS_MODE STATS_MODE_READ FLEX_COUNTER_STATUS enable
sai counter group del PORT_STAT_COUNTER
sai counter poll start PORT_STAT_COUNTER oid:0x1000000000002 PORT_COUNTER_ID_LIST "SAI_PORT_STAT_IF_IN_UCAST_PKTS,SAI_PORT_STAT_IF_OUT_UCAST_PKTS"
sai counter poll stop PORT_STAT_COUNTER oid:0x1000000000002
sai counter get oid:0x1000000000002 SAI_PORT_STAT_IF_IN_UCAST_PKTS SAI_PORT_STAT_IF_OUT_UCAST_PKTS SAI_FAKE_STATS_COUNTER
sai counter get oid:0x1000000000002
sai counter del oid:0x1000000000002
```

### Example of using flex counters in tests

[Simple test with counters](../tests/test_simple_counters.py)

### Possible improvements

* add support for flex counter support for PHY devices (they uses `GB_COUNTERS_DB` and `GB_FLEX_COUNTER_DB`)
* add support for adding plugins (lua scripts) for counter group. Each group could have lua scripts that are run after collection of counters. Examples of plugins: [port_rates.lua](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/port_rates.lua), [port_flr.lua](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/port_flr.lua)
* add support for bulk counter polling for flex counter groups (it would require addition of BULK_CHUNK_SIZE and BULK_CHUNK_SIZE_PER_PREFIX fields for flex counter group with examples)

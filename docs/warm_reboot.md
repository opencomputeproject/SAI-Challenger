# Warm reboot testing support

Warm reboot lets the SAI process exit and restart while the ASIC dataplane keeps forwarding. SAI serializes its object database on shutdown and restores it on the next `sai_api_initialize()` — without reprogramming the ASIC or changing object IDs. This document describes what warm boot is and what was added for this feature.

## Warm reboot flow in SAI

### Phase 1 - before shutdown

1. `SAI_WARM_BOOT_READ_FILE` and `SAI_WARM_BOOT_WRITE_FILE` should be set in `service_method_table_t`
2. `SAI_SWITCH_ATTR_RESTART_WARM=true` is set by Host Adapter
3. `SAI_SWITCH_ATTR_PRE_SHUTDOWN=true` is set by Host Adapter (optional)
4. `SAI_SWITCH_ATTR_UNINIT_DATA_PLANE_ON_REMOVAL=false` is set for each switch by Host Adapter
5. Host Adapter removes switches
6. Host Adapter calls `sai_api_uninitialize`, SAI/SDK state should be dumped to `SAI_WARM_BOOT_WRITE_FILE`

### Phase 2 - after shutdown

1. `SAI_WARM_BOOT_READ_FILE`, `SAI_WARM_BOOT_WRITE_FILE` and `SAI_BOOT_TYPE=1` (0 - cold, 1 - warm, 2 - fast) should be set in `service_method_table_t`
2. Host Adapter calls `sai_api_initialize`
3. Host Adapter creates switch object during which SAI should restore the SAI/SDK state from before shutdown based on `SAI_WARM_BOOT_READ_FILE`. `create_switch` should return the same OID as before. If SAI supports creation of multiple switch objects, the OID should be based on `SAI_SWITCH_ATTR_SWITCH_HARDWARE_INFO`

## Simplified warm reboot flow in SONiC

This section focuses on SONiC warm reboot mainly from the `syncd` point of view. Check [SONiC_Warmboot.md](https://github.com/sonic-net/SONiC/blob/master/doc/warm-reboot/SONiC_Warmboot.md) for a better understanding of warm reboot in general. Warm reboot can be initiated using the [warm-reboot](https://github.com/sonic-net/sonic-utilities/blob/master/scripts/fast-reboot) script.

### Phase 1 - before shutdown

1. `syncd` sets default values for `SAI_WARM_BOOT_READ_FILE` and `SAI_WARM_BOOT_WRITE_FILE` before calling `sai_api_initialize` if they are not set in sai.profile
2. `orchagent` disables FDB aging and FDB learning on all bridge ports.
3. Pre-shutdown message is sent to `syncd` via Redis `RESTARTQUERY` channel, `syncd` sets `SAI_SWITCH_ATTR_RESTART_WARM=true` and `SAI_SWITCH_ATTR_PRE_SHUTDOWN=true`. `syncd` enters waiting mode in which it waits for shutdown request. `syncd` stores pre-shutdown state in `STATE_DB` `WARM_RESTART_TABLE|warm-shutdown` table
4. Warm shutdown message is sent to `syncd`, `syncd` sets `SAI_SWITCH_ATTR_RESTART_WARM=true` and `SAI_SWITCH_ATTR_UNINIT_DATA_PLANE_ON_REMOVAL=false`. `syncd` stores pre-shutdown state in `STATE_DB` `WARM_RESTART_TABLE|warm-shutdown` table
5. `syncd` removes switches
6. `syncd` calls `sai_api_uninitialize` and exits

### Phase 2 - after shutdown

1. In `STATE_DB`, the `enable` field of `WARM_RESTART_ENABLE_TABLE|syncd` table (or `WARM_RESTART_ENABLE_TABLE|system` table) is set to true
2. `syncd` is started
3. `syncd` sets default values for `SAI_WARM_BOOT_READ_FILE` and `SAI_WARM_BOOT_WRITE_FILE` before calling `sai_api_initialize` if they are not set in sai.profile. `syncd` sets `SAI_BOOT_TYPE=1` by checking `WARM_RESTART_ENABLE_TABLE|syncd` table (or `WARM_RESTART_ENABLE_TABLE|system` table)
4. `syncd` initializes SAI API and creates switches. For more details check `Syncd::performWarmRestart()` in [Syncd.cpp](https://github.com/sonic-net/sonic-sairedis/blob/master/syncd/Syncd.cpp)
5. `orchagent` reconciles state from `APP_DB` and `STATE_DB` with `ASIC_DB`

## How warm reboot is performed in SAI-Challenger

Added `perform_warm_boot()` to the `Sai` class and `pre_shutdown()`, `warm_shutdown()`, and `verify_restore_after_warm_shutdown()` to the `SaiClient` class. Currently warm boot support is implemented only for the SAI Redis client; the SAI Thrift client throws an error on the newly added APIs. Check [sai_redis_client.py](../common/sai_client/sai_redis_client/sai_redis_client.py) for more details.

Subclasses of the `Sai` base class may implement additional functionality for `perform_warm_boot()` along with additional validation, as it is done in [sai_npu.py](../common/sai_npu.py)

## Example of testing warm reboot

See [simple warm reboot test](../tests/test_warmboot.py)

## Possible improvements

* Add warm reboot support for SAI Thrift client

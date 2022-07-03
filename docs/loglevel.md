# Logging

The SAI Challenger uses Redis DB as a North-Bound interface and as a configuration and state storage.​ The Redis DB namespace #3 (LOGLEVEL_DB) is used as a logger configuration storage for both SyncD and SAI. On SyncD start, the default SAI log levels for each SAI API are configured through [setSaiApiLogLevel()](https://github.com/Azure/sonic-sairedis/blob/bc7ccc2d5c2ddad53ebd696f81ff3d45aacbf438/syncd/Syncd.cpp#L58):

```sh
> redis-cli​

​127.0.0.1:6379> select 3​
OK​

127.0.0.1:6379[3]> keys *​
1) "SAI_API_IPSEC:SAI_API_IPSEC"​
2) "SAI_API_HOSTIF:SAI_API_HOSTIF"​
       .....​
43) "syncd:syncd"​
       .....​
48) "SAI_API_ROUTE:SAI_API_ROUTE"​

127.0.0.1:6379[3]> hgetall "syncd:syncd"​
1) "LOGLEVEL"​
2) "NOTICE"​
3) "LOGOUTPUT"​
4) "SYSLOG"​

127.0.0.1:6379[3]> hgetall "SAI_API_QUEUE:SAI_API_QUEUE"​
1) "LOGLEVEL"​
2) "SAI_LOG_LEVEL_NOTICE"​
3) "LOGOUTPUT"​
4) "SYSLOG"​
127.0.0.1:6379[3]> ​
```

## Managing loglevels from CLI

The SAI Challenger contains built-in SWSS/SONiC native `swssloglevel` tool that can be used to print current logging levels as well as configure them:

```sh
Usage: swssloglevel [OPTIONS]
SONiC logging severity level setting.

Options:
	 -h	print this message
	 -l	loglevel value
	 -c	component name in DB for which loglevel is applied (provided with -l)
	 -a	apply loglevel to all components (provided with -l)
	 -s	apply loglevel for SAI api component (equivalent to adding prefix "SAI_API_" to component)
	 -p	print components registered in DB for which setting can be applied

Examples:
	swssloglevel -l NOTICE -c orchagent # set orchagent severity level to NOTICE
	swssloglevel -l SAI_LOG_LEVEL_ERROR -s -c SWITCH # set SAI_API_SWITCH severity to ERROR
	swssloglevel -l SAI_LOG_LEVEL_DEBUG -s -a # set all SAI_API_* severity to DEBUG
```

For more details, please refer to:
https://github.com/Azure/sonic-swss-common/blob/master/common/loglevel.cpp

Also, SAI Challenger has `--loglevel` pytest custom option (defaults to `NOTICE`) to set SyncD loglevel on pytest start.​

## Managing loglevels from TCs

The SAI Challenger's base class `Sai` has `set_loglevel()` method that should be used to override default logging level of SAI APIs:

```sh
npu.set_loglevel("VLAN", "DEBUG")
vlan_oid = npu.create(SaiObjType.VLAN, ["SAI_VLAN_ATTR_VLAN_ID", vlan_id])
npu.set_loglevel("VLAN", "NOTICE")
```


# SAI Challenger CLI

Simple Click-based CLI to operate on a dataplane through SAI.

```sh
CLI <--> Redis <--> SyncD <--> SAI
```

## Generic CLI commands

```sh
sai --help
Usage: sai [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  create   Create SAI object
  dump     List SAI object's attribute value
  get      Retrieve SAI object's attributes
  list     List SAI object IDs
  remove   Remove SAI object
  set      Set SAI object's attribute value
  stats    Manage SAI object's stats
  version  Display version info
```

List all supported types of SAI objects
```sh
$ sai list
```

List all SAI objects created so far
```sh
$ sai list all
```

List SAI port objects created so far
```sh
$ sai list port
```

## Usecases

### Configure dataplane manually

Create SAI switch object:
```sh
$ sai create switch SAI_SWITCH_ATTR_INIT_SWITCH true SAI_SWITCH_ATTR_TYPE SAI_SWITCH_TYPE_NPU

Created SAI object SWITCH with oid:0x21000000000000

```

Dump SAI switch object state:
```sh
$ sai dump oid:0x21000000000000
```

Get OIDs of ports:
```sh
$ sai get oid:0x21000000000000  SAI_SWITCH_ATTR_PORT_LIST  SAI_SWITCH_ATTR_TYPE

SAI_SWITCH_ATTR_PORT_LIST                        32:oid:0x1000000000002,oid:0x1000000000003,oid:0x1000000000004,oid:0x1000000000005,oid:0x1000000000006,oid:0x1000000000007,oid:0x1000000000008,oid:0x1000000000009,oid:0x100000000000a,oid:0x100000000000b,oid:0x100000000000c,oid:0x100000000000d,oid:0x100000000000e,oid:0x100000000000f,oid:0x1000000000010,oid:0x1000000000011,oid:0x1000000000012,oid:0x1000000000013,oid:0x1000000000014,oid:0x1000000000015,oid:0x1000000000016,oid:0x1000000000017,oid:0x1000000000018,oid:0x1000000000019,oid:0x100000000001a,oid:0x100000000001b,oid:0x100000000001c,oid:0x100000000001d,oid:0x100000000001e,oid:0x100000000001f,oid:0x1000000000020,oid:0x1000000000021
SAI_SWITCH_ATTR_TYPE                             SAI_SWITCH_TYPE_NPU
```

Get port's statistics:
```sh
$ sai stats get oid:0x1000000000002  SAI_PORT_STAT_IF_IN_UCAST_PKTS  SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS  SAI_PORT_STAT_IF_OUT_OCTETS

SAI_PORT_STAT_IF_IN_UCAST_PKTS                          0
SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS                      0
SAI_PORT_STAT_IF_OUT_OCTETS                             0
```

Clear port's statistics:
```sh
$ sai stats clear oid:0x1000000000002  SAI_PORT_STAT_IF_IN_UCAST_PKTS  SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS  SAI_PORT_STAT_IF_OUT_OCTETS
```


### Debug TC

TBD


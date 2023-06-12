## JSON setup definition

Testbed can be defined in a single file. This allows easily switch from one test setup to another with a single CLI option.
And the test case code does not require to contain any environment specific data.

Testbed file contains:
- DUT info: name, type, connection info, ASIC, SKU, ports, etc.
- Dataplane info: name, type, connection info, ports.

### Common attributes

Here is the list of mandatory attributes for each entry in the testbed configuration. But each specific entry type may contain own attribute types required only by that specific entity.

**alias** - device name used for references in the JSON configuration and in the code.

**asic** - ASIC name as it is defined in `npu/<VENDOR>/` folder.

**target** - target platform name as it is defined in `npu/<VENDOR>/<ASIC>/` folder.

**sku** - SKU name (a file with ports settings) as it is defined in `npu/<VENDOR>/<ASIC>/sku/` folder. Also, the ports configuration can be provided explicitly in the same format as it is defined in SKU configuration file. As an option, this parameters can be set to `null`. In such case, SAI-C will not re-configure ports settings on SAI switch initialization. Because it's expected that the ports will be configured on SAI switch initialization implicitly.

**client** - SAI RPC configuration parameters.

### The `npu` section

```json5
"npu": [
  {
    "alias": "vs",
    "asic": "trident2",
    "target": "saivs",
    "sku": null,
    "client": {
      "type": "redis",
      "config": {
        "ip": "172.17.0.3",
        "port": "6379",
        "loglevel": "NOTICE"
      }
    }
  }
],

```

### The `dataplane` section

The `dataplane` section contains traffic generator related attributes. Bellow there is an example for the default PTF dataplane.

```json5
"dataplane": [
  {
    "alias": "ptf",
    "type": "ptf",
    "mode": "eth",
    "port_groups": [
      {"alias": 0, "name": "veth1"},
      {"alias": 1, "name": "veth2"},
      {"alias": 2, "name": "veth3"},
      {"alias": 3, "name": "veth4"}
    ]
  }
]
```

For more information on dataplane configuration (including **snappi** and HW traffic generators) please refer to [sai_dataplane.md](./sai_dataplane.md) document.


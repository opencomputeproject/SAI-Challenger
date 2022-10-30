## JSON setup definition

Testbed can be defined in a single file. This allows easily switch from one test setup to another with a single CLI option.
And the test case code does not require to contain any environment specific data.

Testbed file contains:
- DUT info: name, type, connection info, ASIC, SKU, ports, etc.
- Dataplane info: name, type, connection info, ports.
- Connections: How the dataplane is connected to the DUT.

### Common attributes

Here is the list of mandatory attributes for each entry in the testbed configuration. But each specific entry type may contain own attribute types required only by that specific entity.

**alias** - device name used for references in the json configuration and in the code.

**port_groups** - description of ports on the devices.

### NPU section

```json5
"NPU": [
  {
    "alias": "vs",
    "asic": "trident2",
    "target": "saivs",
    "type": "vs",
    "sku": null,
    "mode": "client-server",
    "sai_server_ip": "172.17.0.3",
    "port_groups": [{"1x10G": "Ethernet0", "init": "1x10G", "alias": 0},
                    {"1x10G": "Ethernet1", "init": "1x10G", "alias": 1}
                  ],
    "sai_dataplane": "ptf_nn"
  }
]
```

### DATAPLANE section

DATAPLANE section contains traffic generator related attributes. Bellow there is an example for the default PTF dataplane.

```json5
"DATAPLANE": [
  {
    "alias": "ptf",
    "type": "ptf",
    "mode": "eth",
    "port_groups": [{"10G": "veth1", "init": "10G", "alias": 0},
                    {"10G": "veth2", "init": "10G", "alias": 1}
                   ]
  }
]
```

More about dataplane section (including **snappi** and HW traffic generators) - [link](./sai_dataplane.md).

### CONNECTIONS section

CONNECTION sections contains the dictionary of connected devices and port pairs. Use **aliases** to reference necessary device or port_group from the NPU/DPU/PHY and DATAPLANE sections.

```json5
"CONNECTIONS": {
    "ptf->vs": [[0, 0],
                [1, 1]
               ]
}
```

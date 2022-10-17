# Dataplane configuration

**DATAPLANE** attribute of the JSON configuration is responsible for the dataplane configuration.

To choose which implementation to use you should explicitly specify the `type` attribute of the configuration.

## Implementation details

Currently, there are two dataplane types available: **PTF** and **SNAPPI**.
Both of them are implementing *SaiDataplane* interface which is defined in the `common/sai_dataplane.py`.

Dataplane implementation is located under `dataplane` directory. There you can find two directories `ptf` and `snappi` that correspond to the two available dataplane types.

## PTF example

```
"DATAPLANE": [
  {
    "alias": "ptf",
    "type": "ptf",
    "mode": "eth",
    "port_groups": [{"10G": "veth1", "init": "10G", "alias": 0},
                    {"10G": "veth2", "init": "10G", "alias": 1}]
  }
]
```

Where `port_groups` contain two ports: "veth1" and "veth2". "10G" is a port speed at the system start. For PTF, 10G mode does not affect the setup and required only by common `port_groups` implementation. 10G is selected because it is a default Linux kernel VETH driver mode.

## SNAPPI example
```
"DATAPLANE": [
  {
    "alias": "ixia",
    "type": "snappi",
    "mode": "ixia_c",
    "controller": "https://127.0.0.1:443",
    "port_groups": [{"10G": "veth1", "init": "10G", "alias": 0},
                    {"10G": "veth3", "init": "10G", "alias": 1}]
  }
]
```

SNAPPI specific attributes:

`mode` - `ixia_c`/`ixnetwork`/`trex`

`controller` - Depends on `mode`:
* ixia_c - `https://<tgen-ip>:<port>`
* ixnetwork - `https://<tgen-ip>:<port>`
* trex - `<tgen-ip>:<port>`

`port_groups` may contain optional attribute - `location` - which is TG specific URL of the port. The format depends on a particular TG typeb.

Example for Ixia-C:
```
"port_groups": [{"10G": "veth1", "init": "10G", "alias": 0, "location": "127.0.0.1:5555"},
                {"10G": "veth2", "init": "10G", "alias": 1, "location": "127.0.0.1:5556"}]
```

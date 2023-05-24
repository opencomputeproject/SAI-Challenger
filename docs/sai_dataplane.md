# Dataplane configuration

**DATAPLANE** attribute of the JSON configuration is responsible for the dataplane configuration.

To choose which implementation to use you should explicitly specify the `type` attribute of the configuration.

## Implementation details

Currently, there are two dataplane types available: **PTF** and **SNAPPI**.
Both of them are implementing *SaiDataplane* interface which is defined in the `common/sai_dataplane.py`.

Dataplane implementation is located under `common/sai_dataplane/` directory. There you can find two directories `ptf` and `snappi` that correspond to the two available dataplane types.

## PTF example

```
"dataplane": [
  {
    "alias": "ptf",
    "type": "ptf",
    "mode": "eth",
    "port_groups": [
      {"alias": 0, "name": "veth1"},
      {"alias": 1, "name": "veth2"}
    ]
  }
]
```

Where `port_groups` contain two ports: "veth1" and "veth2".

## SNAPPI example
```
"dataplane": [
  {
    "alias": "tg",
    "type": "snappi",
    "mode": "ixia_c",
    "controller": "https://127.0.0.1:8443",
    "port_groups": [
      {"alias": 0, "name": "veth1", "speed": "10G"},
      {"alias": 1, "name": "veth2", "speed": "10G"}
    ]
  }
]
```

SNAPPI specific attributes:

`mode` - `ixia_c`/`ixnetwork`/`trex`

`controller` - Depends on `mode`:
* ixia_c - `https://<tgen-ip>:<port>`
* ixnetwork - `https://<tgen-ip>:<port>`
* trex - `<tgen-ip>:<port>`

`port_groups` may contain optional attribute - `location` - which is TG specific URL of the port. The format depends on a particular TG type.

Example for Ixia-C:
```
"port_groups": [
    {"alias": 0, "name": "veth1", "speed": "10G", "location": "127.0.0.1:5555"},
    {"alias": 1, "name": "veth2", "speed": "10G", "location": "127.0.0.1:5556"}
]
```

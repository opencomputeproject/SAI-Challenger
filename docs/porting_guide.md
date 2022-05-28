# Porting Guide

## Platform folder

Typical platform folder structure:
```sh
platform/
├── <VENDOR>
│   ├── <ASIC-1>
│   │   ├── <TARGET-1>
│   │   │   ├── configs/      (optional)
│   │   │   ├── Dockerfile
│   │   │   ├── Dockerfile.server
│   │   │   └── sku/          (optional)
│   │   ├── <TARGET-2>
│   │   │   ├── configs/
│   │   │   ├── Dockerfile
│   │   │   └── sku/
│   │   └── sai_npu.py        (optional)
│   ├── <ASIC-2>
│   │   └── <TARGET-1>
│   │       ├── configs/
│   │       ├── Dockerfile
│   │       ├── scripts/      (optional)
│   │       └── sku/
│   └── sai_npu.py    (optional)
```

The platform folder MAY contain multiple vendors. Each vendor folder MAY contain 1..n ASICs and optional vendor-specific `sai_npu` module. Each ASIC folder MAY contain 1..n targets (either HW device or simulator or emulator) and optional ASIC-specific `sai_npu` module. Each target's folder MUST contain either Dockerfile for standalone mode or Dockerfile.server for client-server mode or both. Also, the target's folder MAY contain optional `sku/` folder with JSON files that define front panel ports configuration as well as others target-specific files and folders.

E.g.,
```sh
platform/
├── broadcom
│   ├── BCM56850
│   │   └── saivs
│   │       ├── configs/
│   │       ├── Dockerfile
│   │       ├── Dockerfile.server
│   │       └── sku/
│   ├── sai_npu.py
│   └── trident2 -> BCM56850/
└── intel
    ├── README.md
    ├── sai_npu.py
    └── tofino
        ├── model
        │   ├── configs/
        │   ├── Dockerfile
        │   ├── scenarios -> ../montara/scenarios/
        │   ├── scripts/
        │   └── sku/
        └── montara
            ├── scenarios/
            └── sku/
```


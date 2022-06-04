# Porting Guide

SAI Challenger (SC) uses plugin-based approach to build and start a platform specific instance. So, it is expected that a new platform porting process will be as simple as adding a new entry in the `platform/` folder with very limited number of platform specific scripts and configuration files.

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

The platform folder MAY contain multiple vendors. Each vendor folder MAY contain 1..n ASICs and optional vendor-specific `sai_npu` module. Each ASIC folder MAY contain 1..n targets (either HW device or simulator or emulator) and optional ASIC-specific `sai_npu` module. Each target's folder MUST contain either `Dockerfile` for standalone mode or `Dockerfile.server` for client-server mode or both. Also, the target's folder MAY contain optional `sku/` folder with JSON files that define front panel ports configuration as well as others target-specific files and folders.

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

The target specific `Dockerfile` should be based on SC base Docker image created of `Dockerfile` located in SC root folder. Also, it should define `SC_PLATFORM`, `SC_ASIC` and `SC_TARGET` environment variables. These environment variables are used by SC `conftest.py` to properly initialize the test environment.
```sh
FROM sc-base

MAINTAINER your@email.com

ENV SC_PLATFORM=intel
ENV SC_ASIC=tofino
ENV SC_TARGET=model
```

The target specific `Dockerfile.server` should be based on SC base Docker image created of `Dockerfile.server` located in SC root folder.
```sh
FROM sc-server-base

MAINTAINER your@email.com
```


## Running SAI Challenger with VPP in standalone mode

The VPP target allows SAI Challenger test cases to run against a software-based VPP dataplane instead of a physical switch ASIC.

SAI Challenger test cases use the standard SAI API. SAI operations are handled by `sonic-sairedis` and translated into VPP-specific operations, which are then executed by the VPP dataplane.

The VPP standalone environment consists of SAI Challenger, `sonic-sairedis`, Redis, VPP, and the required Linux/VPP interfaces.

### Architecture

The main data path is:

```text
SAI Challenger tests
        │
        ▼
     SAI API
        │
        ▼
   sonic-sairedis
        │
        ▼
    SAI VPP backend
        │
        ▼
       VPP
        │
        ▼
Linux host interfaces / LCP
        │
        ▼
     Test traffic
```

SAI Challenger communicates with the SAI implementation through `sonic-sairedis`. The VPP SAI backend converts SAI operations into VPP operations and uses VPP as the software dataplane.

---

### Build VPP target

Build the SAI Challenger Docker image using the VPP ASIC and `saivpp` target:

```sh
./build.sh -a vpp -t saivpp -o trixie
```

The VPP target currently uses the Trixie base image because the required VPP packages depend on newer system libraries than those available in the Bookworm environment.

### VPP dependencies

The VPP target requires several VPP Debian packages during the Docker image build.

The build process first attempts to download pre-built VPP packages from the SONiC VPP package repository. This avoids rebuilding VPP from source when compatible packages are already available.

If the required packages cannot be downloaded, the build automatically falls back to building VPP locally using a pinned revision of `sonic-platform-vpp`.

The build process therefore follows this flow:

```text
Build VPP image
      │
      ▼
Download pre-built VPP packages
      │
      ├── Success ──────────► Install packages
      │
      └── Download failure
                │
                ▼
       Clone sonic-platform-vpp
                │
                ▼
       Checkout pinned revision
                │
                ▼
          Build VPP locally
                │
                ▼
       Install generated packages
```

---

### Start the VPP environment

Start the VPP standalone environment:

```sh
./run.sh -a vpp -t saivpp -o trixie
```

---

### Run SAI Challenger test cases

Run SAI Challenger tests against the `saivpp_standalone` testbed:

```sh
./exec.sh -a vpp -t saivpp pytest test_l2_basic.py \
    --testbed=saivpp_standalone \
    -v
```

Run a specific test:

```sh
./exec.sh -a vpp -t saivpp pytest test_l2_basic.py \
    --testbed=saivpp_standalone \
    -v -k "test_l2_access_to_access_vlan"
```

Run tests with traffic:

```sh
./exec.sh -a vpp -t saivpp pytest test_l2_basic.py \
    --testbed=saivpp_standalone \
    -v --traffic
```

Run the basic L3 routing test:

```sh
./exec.sh -a vpp -t saivpp pytest test_dc_t1.py \
    --testbed=saivpp_standalone \
    -v -k "test_basic_route"
```

---

### VPP port mapping

SAI/SONiC ports such as `Ethernet1..Ethernet32` are mapped to VPP host interfaces such as `host-eth1..host-eth32`.

The mapping is defined by `sonic_vpp_ifmap.ini`.

Example:

```text
Ethernet1  → host-eth1
Ethernet2  → host-eth2
...
Ethernet32 → host-eth32
```

Each VPP host interface is backed by a corresponding Linux interface used to provide the traffic path between the test environment and the VPP dataplane.

The complete logical path is:

```text
+-----------------------------------+
|            SONiC / SAI            |
|       Ethernet1...Ethernet32      |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|        sonic_vpp_ifmap.ini        |
|       EthernetN -> host-ethN      |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|                VPP                |
|             host-ethN             |
+-----------------------------------+
                  │
                  │ host-ethN -> ethN
                  ▼
+-----------------------------------+
|               Linux               |
|            ethN -> vethN          |
+-----------------------------------+
                  │
                  ▼
+-----------------------------------+
|      Traffic Generator / PTF      |
+-----------------------------------+
```

### Why SONiC ports and LCP interfaces are required

SAI Challenger operates on SONiC/SAI switch ports such as `Ethernet1..Ethernet32`.

These logical ports must be mapped to the corresponding VPP interfaces so that SAI operations can be applied to the correct VPP dataplane interface.

For example:

```text
Ethernet1
    │
    ▼
host-eth1
    │
    ▼
LCP pair
host-eth1 ↔ tap4096
    │
    ▼
Linux / VPP integration
```

The mapping is required for port-related SAI operations. It allows the VPP backend to resolve a SONiC/SAI port to the corresponding VPP interface and apply the operation to the correct dataplane resource.

Without this mapping, the VPP backend cannot properly resolve the target port and operations that depend on the port mapping may fail.

---

### VPP host-interface initialization

The VPP environment creates the required host interfaces during startup.

The host interfaces are created according to the configured port mapping and are made available to the VPP dataplane before SAI operations are performed.

VPP may also create Linux Control Plane (LCP) pairs for the host interfaces:

```text
host-eth1 ↔ tap4096
host-eth2 ↔ tap4097
...
host-eth32 ↔ tap4127
```

The LCP pairs provide the Linux control-plane integration required by the VPP environment.

When the SAI environment is restarted, the VPP interface state is recreated so that the next test run starts from a clean environment.

---

### Monitoring

Check the status of the services inside the container:

```sh
supervisorctl status
```

Check VPP interfaces:

```sh
vppctl show interface
```

Check VPP LCP pairs:

```sh
vppctl show lcp
```

Check VPP hardware interfaces:

```sh
vppctl show hardware-interfaces
```

Check the VPP startup configuration:

```sh
vppctl show version
```

Monitor SAI Challenger and `syncd` logs:

```sh
tail -F /var/log/syslog
```

---

### Supported functionality

The VPP target is primarily intended to provide a software dataplane for SAI Challenger functional testing.

The currently validated functionality includes:

* Basic L2 VLAN forwarding
* L2 access/trunk VLAN operations
* L2 flooding
* FDB operations
* MAC learning and MAC movement
* Basic L3 routing

A basic L3 routing test can be executed with:

```sh
./exec.sh -a vpp -t saivpp pytest test_dc_t1.py \
    --testbed=saivpp_standalone \
    -v -k "test_basic_route"
```

---

### Known limitations

The VPP backend does not currently provide identical behavior for every SAI Challenger test case.

Some features either depend on VPP-specific behavior or are not currently implemented in the VPP backend.

In particular:

* LAG-related tests are currently not supported by the VPP target.
* Some VRF tests currently fail because of unsupported or different VPP behavior.
* Some SAI features may have different semantics compared with a hardware ASIC.

---

### Troubleshooting

If VPP interfaces are missing, first check:

```sh
vppctl show interface
```

If LCP pairs are missing or duplicated:

```sh
vppctl show lcp
```

If `syncd` reports errors related to host interfaces or LCP:

```sh
tail -F /var/log/syslog
```

Typical issues involving stale interfaces can be investigated by checking the current VPP LCP state and restarting the VPP/SAI environment.

If VPP packages cannot be downloaded during the Docker build, the build should automatically fall back to the pinned `sonic-platform-vpp` source revision.

For build failures related to VPP dependencies, verify that the VPP image is being built with the supported Trixie base:

```sh
./build.sh -a vpp -t saivpp -o trixie
```

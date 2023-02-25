<h1>Contents</h1>

- [SAI Challenger Use-Case Scenarios](#sai-challenger-use-case-scenarios)
  - [Common Variations Within the Use-Cases](#common-variations-within-the-use-cases)
    - [DUT Config Variations](#dut-config-variations)
    - [Traffic-Generator Variations](#traffic-generator-variations)
    - [Standalone mode vs. Client-Server Mode](#standalone-mode-vs-client-server-mode)
- [Representative Use-Cases](#representative-use-cases)
  - [Summary](#summary)
  - [Virtual DUT, SW Traffic Generator](#virtual-dut-sw-traffic-generator)
  - [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator)
  - [Physical DUT, self-contained testbed with SW Traffic Generator](#physical-dut-self-contained-testbed-with-sw-traffic-generator)
  - [Physical DUT, HW Traffic Generator](#physical-dut-hw-traffic-generator)
  - [Physical DUT, SW Traffic Generator, Fanout switches](#physical-dut-sw-traffic-generator-fanout-switches)
  - [Umbrella Framework Executing PTF Tests](#umbrella-framework-executing-ptf-tests)

# SAI Challenger Use-Case Scenarios
This section summarizes relevant use-case scenarios along with simple diagrams, in order to convey the wide range of configurations. This is not meant to be all-inclusive; other possibilities exist.

## Common Variations Within the Use-Cases
Each use-case diagram may imply multiple variations of SAI-Challenger and Device Under Test (DUT) solutions; in other words, there are many permutations of any given use-case. 

### DUT Config Variations
The diagram portion below illustrates that SAI Challenger supports both saithrift and sairedis APIs. SAI Challenger test-cases can run over either API without change. A test configuration file selects which API to use.

A given DUT can run, one at a time, either a saithrift RPC server (`saiserver`) or the SONiC `syncd` daemon. A test controller could execute one set of tests over saithrift (with `saiserver` running on the DUT) to verify the DUT via remote libsai calls; then execute the same tests using sairedis (with redis and syncd running on the DUT) to verify partial SONiC integration. The sonic-mgmt testbed has [instructions](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/sai_quality/README.md) for executing PTF-based [sai_qualify](https://github.com/sonic-net/sonic-mgmt/tree/master/tests/sai_qualify) tests, by replacing the `syncd` container with `saiserver`. This same process should work if PTF is replaced with SAI Challenger.

![dut-api-variations](../img/dut-api-variations.svg)

### Traffic-Generator Variations
SAI Challenger can use the [PTF framework](https://github.com/p4lang/ptf), which includes the [Scapy](https://scapy.readthedocs.io/en/latest/) packet generator; or use the [snappi](https://github.com/open-traffic-generator/snappi) APIs to control an [OTG (Open Traffic Generator)](https://github.com/open-traffic-generator)-compliant traffic generator.

For a pure virtual testbed, traffic can flow entirely within internal network devices (veths). For physical DUTs, a software traffic-generator can send traffic onto Ethernet links via the test controller's NIC port(s). Alternatively, for speed and scale, a hardware traffic generator can be controlled by the test server using OTG protocol. This is made easy via Pythonic snappi libraries (golang also available).

PTF embeds the Scapy packet library and has utilities and wrappers to make it easy to craft packets, send, receive and verify them, a packet at a time. It does not support continuous streams of packets, packet-rate scheduling, or flow-tracking.

OTG is supported by a variety of SW and HW-based packet generators. OTG has constructs allowing precision scheduling, multiple flows with built-in tracking, and much more. [ixia-c](https://github.com/open-traffic-generator/ixia-c) is an example of a free, SW-based traffic generator which supports OTG. It has been demonstrated to run at Gbps speeds ([commercial versions](https://www.keysight.com/us/en/products/network-test/protocol-load-test/keysight-elastic-network-generator.html) of ixia-c run close to line rate at 100Gbps). It runs as docker containers and has been deployed in the CI/CD pipelines of open-source projects such as [DASH](https://github.com/sonic-net/DASH) and [Ondatra](https://github.com/openconfig/ondatra). Tests written to run with a SW Traffic Generator can be run on HW as well. 

The recommended way to use OTG traffic-generators is via native snappi methods supporting flow-based constructs. This exposes the full range of capabilities. However, a wrapper library included with SAI Challenger allows OTG traffic generators to be used via familiar PTF helper methods. These create trivial "flows" of one packet to immitate the behaior of Scapy. The benefit of these wrappers is to allow existing, or even new, PTF tests to take advantage of OTG-capable traffic generators (SW or HW), using legacy dataplane helpers.

To summarize, test-cases can send/receive packets using three approaches:
* PTF Dataplane (Scapy-based) using PTF helper classes - SW traffic generator only
* Native snappi (OTG-based) using flow-based APIs - SW or HW OTG generators
* PTF wrappers around snappi API, for PTF backwards-compatibility - SW or HW traffic generators

The diagram below shows a superset of these possibilities. Follow the arrows starting from the "Test Case" icon to see which APIs can be used to control the intended type of traffic generator and physical/virtual traffic connections.

![tgen-variations](../img/tgen-variations.svg)

### Standalone mode vs. Client-Server Mode

SAI Challenger can be executed in two modes:
1. [standalone mode](docs/standalone_mode.md) - both syncd and pytest are running in the same Docker container. This mode is generally only suitable for PTF dataplane testing, because everything is onside the same Docker container. OTG traffic-generator tests controlled by snappi require separate containers.

<a href="url"><img src="../img/sai-challenger-sm.svg" align="center" width="500" ></a>


2. [client-server mode](docs/client_server_mode.md) - syncd and pytest are running in the separate Docker containers.

<a href="url"><img src="../img/sai-challenger-cs.svg" align="center" width="500" ></a>

The standalone mode **SHOULD** be used in case of:
- running TCs on vslib SAI implementation
- running TCs without traffic (without `--traffic` option) on HW
- running TCs with/without traffic on ASIC simulator when it also runs inside the same Docker container as syncd or sai_thrift server

The client-server mode **CAN** be used in all the cases defined for the standalone mode, and **MUST** be used in case of:
- running TCs with traffic (with `--traffic` option) on HW
- running TCs with traffic on ASIC simulator when it also runs inside the same Docker container as syncd or sai_thrift server but exposes ports outside the container

# Representative Use-Cases
## Summary
The following diagram shows a high-level view of various use-case scenarios; others are possible. You can click on the title above each diagram to jump to a section which describes it in greater detail.


| [Virtual DUT, SW Traffic Generator](#virtual-dut-sw-traffic-generator) | [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator) | [Physical DUT self-contained testbed with SW Traffic Generator](#physical-dut-self-contained-testbed-with-sw-traffic-generator) |
| ---- | ---- | ---- |
![saic-virtual-dut-sw-tgen-mini](../img/saic-virtual-dut-sw-tgen-mini.svg) |![saic-physical-dut-sw-tgen-mini](../img/saic-physical-dut-sw-tgen-mini.svg) |![saic-physical-dut-sw-tgen-self-contained-mini](../img/saic-physical-dut-sw-tgen-self-contained-mini.svg)

[Physical DUT, HW Traffic Generator](#physical-dut-hw-traffic-generator) | [Physical DUT, SW Traffic Generator, Fanout switches](#physical-dut-sw-traffic-generator-fanout-switches)
| ---- | ---- |
![saic-physical-dut-hw-tgen-mini](../img/saic-physical-dut-hw-tgen-mini.svg) |![saic-physical-dut-sw-tgen-fanout-mini](../img/saic-physical-dut-sw-tgen-fanout-mini.svg) 

|[Umbrella Framework Executing PTF Tests](#umbrella-framework-executing-ptf-tests)|
| --- |
![saic-ptf-sw-tgen-mini](../img/saic-ptf-sw-tgen-mini.svg)
## Virtual DUT, SW Traffic Generator
Summary:
* SAI-Challenger runs on the test host
* The DUT is a SW dataplane running on the same test host.
* SAI-Challenger is virtually cabled to the software DUT using veth connections.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using internal management network.
* Software traffic generation using host's veth ports, can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-virtual-dut-sw-tgen](../img/saic-virtual-dut-sw-tgen.svg)

## Physical DUT, SW Traffic Generator
Summary:
* SAI-Challenger runs on the test host
* The DUT is a physically separate device, whether a network switch, xPU or SW dataplane running on a server.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using a management network.
* Software traffic generation using host's NIC port(s), can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-physical-dut-sw-tgen](../img/saic-physical-dut-sw-tgen.svg)

## Physical DUT, self-contained testbed with SW Traffic Generator
This is a variation on the previous use-case [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator), but is entirely self-contained on the physical DUT.
>**Note:** This has not been tried yet. This is a concept only. Details of running SAI Challenger on a DUT are TBD. It should be straightforward.

Summary:
* SAI-Challenger runs on the DUT itself
* The DUT is a physically separate device, whether a network switch, xPU or SW dataplane running on a server.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using internal management network.
* Software traffic generation using internal, platform-dependent "CPU-to-Switch ASIC" port(s), can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

* Details of how traffic is conveyed between the DUT's CPU and the switching device are platform-specific (e.g. CPU NIC wired to special management port on the switch ASIC). SAI Challenger contains no specific support for this use-case, but if standard netdevs can be used, it should be possible. Likewise, the traffic must ingress and egress the DUT's "front panel" ports using various platform-specific techniques such as loopbacks, recirculation, etc.

![saic-physical-dut-sw-tgen-self-contained](../img/saic-physical-dut-sw-tgen-self-contained.svg)

## Physical DUT, HW Traffic Generator
Summary:
* SAI-Challenger runs on the test host
* The DUT is a physically separate device, whether a network switch, xPU or SW dataplane running on a server.
* Test controller is directly cabled to a physical DUT using Ethernet
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities.
* [OTG](https://github.com/open-traffic-generator) hardware traffic generator such as Ixia chassis.

![saic-physical-dut-hw-tgen](../img/saic-physical-dut-hw-tgen.svg)

## Physical DUT, SW Traffic Generator, Fanout switches
This use-case is similar to the [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator) use-case. Instead of a direct connection from the Test Server's NIC ports to a DUT port, one or more fanout switches are used to steer packets (e.g. via VLAN tags and fanout switching rules) to a large number of DUT traffic ports. This technique is used in the [sonic-mgmt testbed](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/README.testbed.Overview.md).

>**Note:** This has not been tried yet. This is a concept only.

Summary:
* SAI-Challenger runs on the test host
* The DUT is a physically separate device, whether a network switch, xPU or SW dataplane running on a server.
* Test controller is cabled to a fanout switch complex (one or more tiers) using Ethernet.
* Fanout switch complex is cabled to the DUT traffic ports.
* Details such as control-plane application VMs, open-vswitch, etc. as used in sonic-mgmt are omitted for clarity and are outside the scope of SAI Challenger. Here, SAI Challenger replaces the role of PTF in sonic-mgmt testbed.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities.
* Software traffic generation using host's NIC port(s), can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-physical-dut-sw-tgen-fanout](../img/saic-physical-dut-sw-tgen-fanout.svg)


For reference, the sonic-mgmt generic topology is shown below. Refer to [sonic-mgmt testbed](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/README.testbed.Overview.md) for more detailed information.

<a href="url"><img src="https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/img/physical_connection.png" align="center" width="500" ></a>


## Umbrella Framework Executing PTF Tests
SAI-Challenger can act as an umbrella test framework for traditional PTF (e.g. SAI-PTF) test cases.

In this scenario, pictured below, SAI-Challenger can run two types of tests:
* **Native SAI Challenger tests**: These use the PyTest framework. These can take advantage of every SAI Challenger capability  as described in this document.
* **Native PTF tests**: SAI Challenger invokes PTF test-cases by calling the PTF executable to run PTF tests "natively." In so doing, it passes it the appropriate PTF port configuration parameters on the command-line, which are extracted and translated from SAI Challenger native test config files. This makes for a more convenient and integrated test environment. While in this mode, only the native PTF dataplane methods and DUT config API (saithrift) are available, because that is what are supported by SAI-PTF.


For brevity, only one scenario is shown in the diagram below: a test server with SW traffic-generators, feeding a DUT. However, the unbrella framework concept is equally applicable to other scenarios such as:

* [Virtual DUT, SW Traffic Generator](#virtual-dut-sw-traffic-generator) or [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator)
* [Physical DUT, SW Traffic Generator, Fanout switches](#physical-dut-sw-traffic-generator-fanout-switches)
* [Physical DUT, self-contained testbed with SW Traffic Generator](#physical-dut-self-contained-testbed-with-sw-traffic-generator)

Summary:
* SAI-Challenger scenarios which utilize a SW traffic generator, can also invoke PTF test cases as an umbrella test framework.
* PTF tests executed by SAI Challenger only support traditional PTF-Scapy packet generation utility methods and can only configure the DUT using saithrift.
* Applicable to virtual or physical DUT testing.

![saic-ptf-sw-tgen](../img/saic-ptf-sw-tgen.svg)
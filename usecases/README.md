<h1>Contents</h1>

- [SAI Challenger Use-case Summary](#sai-challenger-use-case-summary)
  - [Common Variations Within a Use-Case](#common-variations-within-a-use-case)
    - [DUT Config Variations](#dut-config-variations)
    - [Traffic-Generator Variations](#traffic-generator-variations)
  - [Virtual DUT, SW Traffic Generator](#virtual-dut-sw-traffic-generator)
  - [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator)
  - [Physical DUT, SW Traffic Generator, Test Controller on the DUT](#physical-dut-sw-traffic-generator-test-controller-on-the-dut)
  - [Physical DUT, HW Traffic Generator](#physical-dut-hw-traffic-generator)
  - [Physical DUT, SW Traffic Generator, Fanout switches](#physical-dut-sw-traffic-generator-fanout-switches)
  - [Physical DUT, HW Testbed-in-a-box](#physical-dut-hw-testbed-in-a-box)

# SAI Challenger Use-case Summary
This section summarizes relevant use-cases along with simple diagrams, in order to convey the wide range of applications.

## Common Variations Within a Use-Case
Each use-case diagram may imply multiple variations of SAI-Challenger and Device Under Test (DUT) capabilities; in other words, there are many permutations of any given use-case. 

### DUT Config Variations
The diagram portion below illustrates that SAI Challenger supports both saithrift and sairedis APIs. SAI Challenger test-cases can run over either API without change. A test configuration file selects which API to use.

A given DUT can have a running saithrift RPC server (`saiserver`) or a SONiC `syncd` daemon linked to `libsai`. Only one may be executing at a time. A test controller could execute one set of tests over saithrift (with `saiserver` running on the DUT) to verify libsai in isolation; then execute the same tests using sairedis (with redis and syncd running on the DUT) to verify partial SONiC integration. The details of loading and running these services is covered elsewhere.

![dut-api-variations](../img/dut-api-variations.svg)

### Traffic-Generator Variations
SAI Challenger can use the [PTF framework](https://github.com/p4lang/ptf), which includes the [Scapy](https://scapy.readthedocs.io/en/latest/) packet generator; or use the snappi APIs to control an [OTG (Open Traffic Generator)](https://github.com/open-traffic-generator)-compliant traffic generator.

PTF embeds the Scapy packet library and has utilities and wrappers to make it easy to craft packets, send and receive them, a packet at a time. It does not support continuous streams of packets, packet-rate scheduling, or flow-tracking.

OTG is supported by a variety of SW and HW-based packet generators. OTG has constructs allowing precision scheduling, multiple flows with built-in tracking, and much more. [ixia-c](https://github.com/open-traffic-generator/ixia-c) is an example of a free, SW-based traffic generator which supports OTG. It runs as docker containers and has been deployed in the CI/CD pipelines of open-source projects such as [DASH](https://github.com/sonic-net/DASH). Tests written to run with a SW  Traffic Generator can be run on HW as well.

For a pure virtual testbed, traffic can flow entirely within internal network devices (veths). For physical DUTs, a software traffic-generator can send traffic onto Ethernet links via the test controller's NIC card(s). Alternatively, for speed and scale, a hardware traffic generator can be controlled by the test server using OTG protocol via the snappi API within test cases.

The diagram below shows a superset of these possibilities:

![tgen-variations](../img/tgen-variations.svg)

## Virtual DUT, SW Traffic Generator
Summary:
* Everything runs on the test host
* SAI-Challenger is virtually cabled to a software DUT using veth connections.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using internal management network.
* Software traffic generation using host's veth ports, can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-virtual-dut-sw-tgen](../img/saic-virtual-dut-sw-tgen.svg)

## Physical DUT, SW Traffic Generator
Summary:
* SAI-Challenger runs on the test host
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using a management network.
* Software traffic generation using host's NIC port(s), can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-physical-dut-sw-tgen](../img/saic-physical-dut-sw-tgen.svg)

## Physical DUT, SW Traffic Generator, Test Controller on the DUT
This is a variation on the previous use-case [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator), but is entirely self-contained on the physical DUT.

Summary:
* SAI-Challenger runs on the DUT itself
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using internal management network.
* Software traffic generation using internal, platform-dependent "CPU-to-Switch ASIC" port(s), can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

* Details of how traffic is conveyed between the DUT's CPU and the switching device are platform-specific (e.g. CPU NIC wired to special management port on the switch ASIC). SAI Challenger contains no specific support for this use-case, but if standard netdevs can be used, it should be possible. Likewise, the traffic must ingress and egress the DUT's "front panel" ports using various platform-specific techniques such as loopbacks, recirculation, etc.

![saic-physical-dut-sw-tgen-no-host](../img/saic-physical-dut-sw-tgen-no-host.svg)

## Physical DUT, HW Traffic Generator
Summary:
* SAI-Challenger runs on the test host
* Test controller is physically cabled to a physical DUT using Ethernet
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities.
* [OTG](https://github.com/open-traffic-generator) hardware traffic generator such as Ixia chassis.

![saic-physical-dut-hw-tgen](../img/saic-physical-dut-hw-tgen.svg)

## Physical DUT, SW Traffic Generator, Fanout switches
This use-case is similar to the [Physical DUT, SW Traffic Generator](#physical-dut-sw-traffic-generator) use-case. Instead of a direct connection from the Test Server's NIC ports to a DUT port, one or more fanout switches is used to steer packets via VLAN tags and fanout switching rules to a large number of DUT front panel ports. This technique is used in the [sonic-mgmt testbed](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/README.testbed.Overview.md).

Summary:
* SAI-Challenger runs on the test host
* Test controller is physically cabled to a fanout switch complex using Ethernet.
* Details such as control-plane application VMs, open-vswitch, etc. as used in sonic-mgmt are omitted for clarity and are outside the scope of SAI Challenger. Here, SAI Challenger replaces the role of PTF in sonic-mgmt testbed.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities.
* Software traffic generation using host's NIC port(s), can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-physical-dut-sw-tgen-fanout](../img/saic-physical-dut-sw-tgen-fanout.svg)



For reference, the sonic-mgmt generic topology is shown below:

<a href="url"><img src="https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testbed/img/physical_connection.png" align="center" width="500" ></a>

## Physical DUT, HW Testbed-in-a-box
This use-case takes advantage of an all-in-one SW/HW testbed-in-a-box. Such a device, such as the [Keysight UHD100T32](https://www.keysight.com/us/en/assets/7019-0482/data-sheets/UHD100T32-QSFP28-Ultra-High-Density-32-Port-Test-System.pdf), merges the test controller, fanout switches, cEOS VMs, and PTF test framework, inside of a single appliance. In essence, it replace one or more test servers and one or more network switches, with a single box.

In principle the SAI Challenger test framework would also run inside the same device, resulting in a compact solution. It has not yet been proven, this is a concept.

Summary:
* SAI-Challenger runs on the test host
* Test controller, control-plane application VMs, fanout switches and SW traffic generators are all embedded in a single appliance.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities.
* Software traffic generation using test host CPU, can use either or both:
  *  PTF/Scapy (packet-at-a-time)
  *  [OTG](https://github.com/open-traffic-generator) software traffic generator such as ixia-c (flow-based testing).

![saic-physical-dut-testbed-in-a-box](../img/saic-physical-dut-testbed-in-a-box.svg)


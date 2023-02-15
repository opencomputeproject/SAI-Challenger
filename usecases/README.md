# SAI Challenger Use-case Summary
This section summarizes relevant use-cases along with simple diagrams, in order to convey the wide range of applications.

## Common Variations Withing a Use-Case
Each use-case diagram may imply multiple variations of SAI-Challenger and Device Under Test (DUT) capabilities; in other words, there are many permutations of any given use-case. 

### DUT Config Variations
The diagram portion below illustrates that SAI Challenger supports both saithrift and sairedis APIs. SAI Challenger test-cases can run over either API without change. A test configuration file selects which API to use.

A given DUT can have a running saithrift RPC server (`saiserver`) or a SONiC `syncd` daemon linked to `libsai`. Only one may be executing at a time. A test controller could execute one set of tests over saithrift (with `saiserver` running on the DUT) to verify libsai in isolation; then execute the same tests using sairedis (with redis and syncd running on the DUT) to verify partial SONiC integration. The details of loading and running these services is covered elsewhere.

![dut-api-variations](../img/dut-api-variations.svg)

### Traffic-Generator Variations
SAI Challenger can use the PTF framework, which includes the Scapy packet generator; or use the snappi APIs to control an [Open Traffic Generator](https://github.com/open-traffic-generator) compliane traffic generator. These support a variey of SW and HW-based packet generators.

For a pure virtual testbed, traffic can flow entirely within internal network devices (veths). For physical DUTs, a software traffic-generator can send traffic onto Ethernet links via the test controller's NIC card(s). Alternatively, for speed and scale, a hardware traffic generator can be controlled by the test server using OTG protocol via the snappi API within test cases.

The diagramn below shows a superset of these possibilities.

![tgen-variations](../img/tgen-variations.svg)

## Virtual DUT, SW Traffic Generator
Summary:
* Everything runs on the test host
* SAI-Challenger is virtually cabled to a software DUT using veth connections.
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities, using internal socket connections.
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

## Physical DUT, HW Traffic Generator
Summary:
* SAI-Challenger runs on the test host
* Test controller is physically cabled to a physical DUT using Ethernet
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times), depending upon DUT capabilities.
* [OTG](https://github.com/open-traffic-generator) hardware traffic generator such as Ixia chassis.

![saic-physical-dut-hw-tgen](../img/saic-physical-dut-hw-tgen.svg)
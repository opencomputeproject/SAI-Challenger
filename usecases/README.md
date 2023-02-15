# SAI Challenger Use-case Summary
This section summarizes relevant use-cases along with simple diagrams, in order to convey the wide range of applications.

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
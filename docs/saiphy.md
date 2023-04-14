# External PHY testing with SAI Challenger

## PHY SAI object model

PHY is treated as a Layer-1 switch. The Switch Abstraction Interface (SAI) API is used as a common PHY abstraction interface:
* SAI_OBJECT_TYPE_SWITCH - defines PHY object
* SAI_OBJECT_TYPE_PORT - defines system side and line side ports
* SAI_OBJECT_TYPE_PORT_CONNECTOR - connects system side and line side ports

<a href="url"><img src="../img/sai-c-phy.svg" align="center" width="600" ></a>

For more information please refer to [SAI Gearbox API Proposal](https://github.com/opencomputeproject/SAI/blob/master/doc/macsec-gearbox).

## PHY development board use case

Summary:
* SAI-Challenger runs on the test host.
* The DUT (PHY development board) is a physically separate device connected to the test host though a management connection (e.g., USB, Eth, PCIe).
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times) running on top of PHY SDK on the test host.
* The hardware traffic generator cabled to a physical DUT.
* [OTG](https://github.com/open-traffic-generator) hardware traffic generator such as Ixia chassis.

![sai-c-libsaiphy](../img/sai-c-libsaiphy.svg)

## SONiC external PHY use case

[TBD]

For more information please refer to [SONiC Gearbox Manager HLD](https://github.com/sonic-net/SONiC/blob/master/doc/gearbox/gearbox_mgr_design.md).

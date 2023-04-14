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
* SAI Challenger runs on the test host.
* The DUT (PHY development board) is a physically separate device connected to the test host though a management connection (e.g., USB, Eth, PCIe).
* The DUT is controlled via SAI-thrift, sairedis, or both (at different times) running on top of PHY SDK on the test host.
* [OTG](https://github.com/open-traffic-generator) hardware traffic generator, such as Ixia chassis, cabled to a physical DUT.

![sai-c-libsaiphy](../img/sai-c-libsaiphy.svg)

## SONiC external PHY use case

Summary:
* SAI Challenger client runs on the test host.
* SONiC DUT with external PHY devices is connected to the test host though a management connection.
* SAI Challenger controls both types of the devices - NPU and external PHYs - via SAI-thrift or sairedis. This can be considered as a multi-DUT topology where NPU and external PHYs should be configured separately.
* [OTG](https://github.com/open-traffic-generator) hardware traffic generator, such as Ixia chassis, cabled to a physical SONiC DUT.

![sai-c-sonic-phy](../img/sai-c-sonic-phy.svg)

For more information please refer to [SONiC Gearbox Manager HLD](https://github.com/sonic-net/SONiC/blob/master/doc/gearbox/gearbox_mgr_design.md).

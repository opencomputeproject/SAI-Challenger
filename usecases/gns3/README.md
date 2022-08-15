# GNS3 use-case

Graphical Network Simulator-3 (GNS3) is a network software emulator. It allows the combination of virtual and real devices, used to simulate complex networks. GNS3 allows to run a small topology consisting of only a few devices on your laptop, to those that have many devices hosted on multiple servers or even hosted in the cloud.

For more information, please refer to GNS3 official documentation:
https://docs.gns3.com/docs/

## Running SAI Challenger server as GNS3 appliance

Build SAI Challenger TD2 SAIVS Docker image:
```sh
./build.sh -i server
```

Install GNS3 as per https://docs.gns3.com/docs/getting-started/installation/linux with uBridge enabled (will be proposed to enable during GNS3 installation).

Fix uBridge permissions:
```sh
sudo chmod 755 /usr/bin/ubridge
```

Start GNS3 and import SAI Challenger appliance file from [File] -> [Import appliance]. Then follow the on-screen instructions to create the template defined in the appliance file. The template of SAI Challenger will be added to the list of Routers.

Add SAI Challenger Server instance to you GNS3 project and make required connections. Note, SAI Challenger Server's `eth0` is a dummy port and should not be used.

Open SAI Challenger appliance's auxiliary console (right click on SAI Challenger Server instance and select from the menu) and start SAI Challenger configuration through SAI CLI.

E.g.,
```sh
sai create switch SAI_SWITCH_ATTR_INIT_SWITCH true SAI_SWITCH_ATTR_TYPE SAI_SWITCH_TYPE_NPU
sai list all
sai dump oid:0x21000000000000
```


# PINS use-case

P4 Integrated Network Stack (PINS) is a project that provides additional components and changes to SONiC and allows the stack to be remotely controlled using P4 and P4RT. To add SDN support, PINS introduces a few new components into the SONiC system:

- P4RT: An application that receives P4 programming requests from the controller and programs the requests to the APPL DB.
- P4Orch: A new orch that programs the P4RT table from APPL DB to ASIC DB. It also sends response notifications to P4RT and manages the APPL STATE DB.

For more information, please refer to SONiC PINS HLD:
https://github.com/sonic-net/SONiC/blob/master/doc/pins/pins_hld.md

## Running PINS use-case

PINS Docker image can be built either as a SAI Challenger standalone image or as a server image.

### Running PINS in a standalone mode

Build PINS image:
```sh
./build.sh
cd usecase/pins/
docker build -t sc-pins .
```

Start PINS container:
```sh
docker run --name sc-pins-run -v $(pwd):/sai-challenger --cap-add=NET_ADMIN --device /dev/net/tun:/dev/net/tun -d sc-pins
```

### Running PINS in a server mode

Build PINS image:
```sh
./build.sh -i server
cd usecase/pins/
docker build --build-arg BASE_IMAGE=sc-server-trident2-saivs -t sc-pins .
```

Start PINS container:
```sh
docker run --name sc-pins-run --cap-add=NET_ADMIN --device /dev/net/tun:/dev/net/tun -d sc-pins
```

### PINS configuration

TODO


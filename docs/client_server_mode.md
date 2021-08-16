## To run SAI Challenger tests on top of vslib in client-server mode

In client-server mode, SAI server - syncd linked with vslib - runs in one Docker container.
Whereas the client - SAI Challenger - runs in the separate Docker container. These two Docker containers can also be running on the separate physical hosts.

Build Docker image with vslib SAI implementation:
```sh
docker build -f Dockerfile.saivs.server -t saivs-server .
```

Build SAI Challenger Docker image with SAI tests:
```sh
docker build -f Dockerfile.client -t sai-challenger-client .
```

Run SAI server:
```sh
docker run --name saivs \
	--cap-add=NET_ADMIN \
	--device /dev/net/tun:/dev/net/tun \
	-d saivs-server
```

Run SAI Challenger testcases:
```sh
docker run --name sai-challenger \
	-v $(pwd):/sai-challenger \
	--cap-add=NET_ADMIN \
	--device /dev/net/tun:/dev/net/tun \
	-d sai-challenger-client

docker exec -ti sai-challenger pytest --sai-server=<saivs-server-ip> --traffic -v test_l2_basic.py
```

**NOTE:** The option `--traffic` will be ignored when running on vslib SAI implementation.


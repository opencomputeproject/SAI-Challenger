## To start SAI Challenger on top of vslib SAI implementation

The vslib SAI implementation is used as a virtual data-plane interface in SONiC Virtual Switch (SONiC VS). Though it does not configure the forwarding path but still process SAI CRUD calls in proper manner. This allows to use vslib for SAI testcases development without running traffic.

Build SAI Challenger Docker image with vslib SAI implementation:
```sh
docker build -f Dockerfile.saivs -t saivs-challenger .
```

Start SAI Challenger:
```sh
docker run --name sai-challenger-run \
	-v $(pwd):/sai-challenger \
	--cap-add=NET_ADMIN \
	--device /dev/net/tun:/dev/net/tun \
	-d saivs-challenger
```

## To start SAI Challenger on top of vendor-specific SAI implementation

Copy Debian package with SAI library into sai-challenger/ folder.

Build SAI Challenger Docker image with vendor-specific SAI implementation:
```sh
docker build -f Dockerfile.sai -t sai-challenger .
```

Start SAI Challenger
```sh
docker run --name sai-challenger-run \
	-v $(pwd):/sai-challenger \
	--cap-add=NET_ADMIN \
	--device /dev/net/tun:/dev/net/tun \
	-d sai-challenger
```

## To run SAI Challenger testcases in standalone mode

Run SAI Challenger testcases:
```sh
docker exec -ti sai-challenger-run pytest -v
```

Run SAI Challenger testcases and generate HTML report:
```sh
docker exec -ti sai-challenger-run pytest -v \
	--html=report.html --self-contained-html
```


## To start SAI Challenger on top of SAI implementation for Tofino Model
Update submodules
```sh
git submodule update --init recursive
```
Copy Debian packages with Intel SDK and Tofino Model into the root folder
of SAI Challenger sources:
```sh
bfnsdk_1.0.0_amd64.deb
bfnplatform_1.0.0_amd64.deb
```

Build SAI Challenger Docker image with SAI implementation for Tofino Model:
```sh
docker build -f Dockerfile.saivs.intel -t saivs-challenger-intel .
```

Start SAI Challenger:
```sh
docker run --name sai-challenger-run \
	-v $(pwd):/sai-challenger \
	--device /dev/net/tun:/dev/net/tun \
	--privileged \
	-d saivs-challenger-intel
```

## To run SAI Challenger testcases on top of Tofino Model

Run SAI Challenger testcases:
```sh
docker exec -ti sai-challenger-run pytest --npu=tofino --sku=tofino_32x100g -v
```
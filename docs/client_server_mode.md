## Running SAI Challenger in client-server mode

### Prepare docker images

Build client Docker image
```sh
./build.sh -i client
```

Build server Docker image for ASIC `trident2` target `saivs`:
```sh
./build.sh -i server -a trident2 -t saivs
```

### Start docker environment

Start SAI Challenger client:
```sh
./run.sh -i client
```

Start SAI Challenger server:
```sh
./run.sh -i server -a trident2 -t saivs
```

Create veth links between client and server dockers:
```sh
bash -c ./veth-create-host.sh sc-server-run sc-client-run
```
Where: _sc-server-run_ and _sc-client-run_ are docker names of SAI-Challenger server and client respectively.

Alternatively, you can run the whole client-server environment on the same host with a single script:
```sh
./run_client_server.sh start -a trident2 -t saivs
./run_client_server.sh start
```

And then shut it down:
```sh
./run_client_server.sh stop
```

### Execute test cases

Run SAI Challenger testcases:
```sh
./exec.sh -i client pytest --setup=../setups/saivs_client_server.json -v -k "test_l2_basic"
```

Run SAI Challenger testcases and generate HTML report:
```sh
./exec.sh -i client pytest --setup=../setups/saivs_client_server.json -v -k "test_l2_basic" --html=report.html --self-contained-html
```

**NOTE:** The option `--traffic` will be ignored when running on `saivs` target.


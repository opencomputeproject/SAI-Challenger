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
./veth-create-host.sh sc-server-run sc-client-run
```
Where: _sc-server-run_ and _sc-client-run_ are docker names of SAI-Challenger server and client respectively. (sc-server-trident2-saivs-run and sc-client-run)

Alternatively, you can run the whole client-server environment on the same host with a single script:
```sh
./run_client_server.sh -a trident2 -t saivs start
./run_client_server.sh start
```

And then shut it down:
```sh
./run_client_server.sh stop
```

### Execute test cases

Run SAI Challenger testcases:
```sh
./exec.sh -i client pytest --testbed=saivs_client_server -v -k "test_l2_basic"
```

Run SAI Challenger testcases and generate HTML report:
```sh
./exec.sh -i client pytest --testbed=saivs_client_server -v -k "test_l2_basic" --html=report.html --self-contained-html
```

**NOTE:** The option `--traffic` will be ignored when running on `saivs` target.

In order to see the syncd log you need to connect to the `server`:
```
docker exec -it sc-server-trident2-saivs-run bash
```
And check  `/var/log/syslog`

To see the input of the redis-server you need to install tcpdump and run it while tests are running:
```
sudo apt install -y tcpdump
sudo tcpdump port 6379
```


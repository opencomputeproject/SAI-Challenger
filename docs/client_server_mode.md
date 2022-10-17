## Running SAI Challenger in client-server mode

First you need to install dependencies:
```
sudo apt update
sudo apt install -y git docker docker.io
sudo usermod -aG docker $USER
```

**NOTE**: It's recommended to use official Docker installation guide.

### Clone repository
```
git clone https://github.com/opencomputeproject/SAI-Challenger
cd SAI-Challenger
git submodule update --init --recursive
git checkout multi-api-support
```

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
Where: _sc-server-run_ and _sc-client-run_ are docker names of SAI-Challenger server and client respectively. (sc-server-trident2-saivs-run and sc-client-run)

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

In order to see the syncd log you need to connect to the `server`:
```
docker exec -it sc-server-trident2-saivs-run bash
```
And check  `/var/log/messages`

To see the input of the redis-server you need to install tcpdump and run it while tests are running:
```
sudo apt install -y tcpdump
sudo tcpdump port 6379
```


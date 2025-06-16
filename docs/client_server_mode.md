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

In case the target Docker image is intended to be built using the private repo that includes some sairedis and/or sai headers extensions the repository credentials should be passed.
For example: the sonic-sairedis git-hub URL for the npu/broadcom/BCM56850/saivs/Dockerfile target is changed to: https://${GIT_UNAME}:${GIT_TOKEN}@github.com/private-repo/sonic-sairedis.git
```bash
ARG BASE_OS
FROM sc-base:${BASE_OS}

ARG GIT_UNAME
ARG GIT_TOKEN

ENV SC_PLATFORM=broadcom
ENV SC_ASIC=BCM56850
ENV SC_TARGET=saivs

WORKDIR /sai

RUN git clone https://${GIT_UNAME}:${GIT_TOKEN}@github.com/private-repo/sonic-sairedis.git \
        && cd sonic-sairedis \
... # 
```

Build the Docker image for ASIC `trident2` target `saivs` from the private repositories: ${GIT_UNAME}:${GIT_TOKEN}
```sh
./build.sh -i client -g user_mame user_token
./build.sh -i server -a trident2 -t saivs -g user_mame user_token
```

**NOTE:** The "user_mame" and "user_token" are private repository user name and http token.

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
sudo ./veth-create-host.sh sc-server-run sc-client-run
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


## Running SAI Challenger in standalone mode

Build Docker image for ASIC `trident2` target `saivs`:
```sh
./build.sh -a trident2 -t saivs
```

**NOTE:** The `saivs` target - defined in sonic-sairedis - is used as a virtual data-plane interface in SONiC Virtual Switch (SONiC VS). Though it does not configure the forwarding path but still process SAI CRUD calls in proper manner. This allows to use `saivs` for SAI testcases development without running traffic.

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
... # Rest of the docker file
```

Build the Docker image for ASIC `trident2` target `saivs` from the private repositories: ${GIT_UNAME}:${GIT_TOKEN}
```sh
./build.sh -a trident2 -t saivs -g user_mame user_token
```

**NOTE:** The "user_mame" and "user_token" are private repository user name and http token.

Start Docker container:
```sh
./run.sh -a trident2 -t saivs
```

Run SAI Challenger testcases:
```sh
./exec.sh -t saivs pytest --testbed=saivs_standalone -v -k "test_l2_basic"
```

Run SAI Challenger testcases and generate HTML report:
```sh
./exec.sh -t saivs pytest --testbed=saivs_standalone -v -k "test_l2_basic" --html=report.html --self-contained-html
```


# SAI Challenger
SAI testing and integration framework for any SAI oriented devices. The main ideas behind SAI-Challenger are:
- testbed agnostic test cases - test case code does not require any changes for running in any type of environment - HW, emulation, different test equipment, links, servers, etc.;
- decoupling real SAI RPC implementation from test cases code - test code looks similar for configuring device using Thrift, Redis, etc.;
- traffic generator agnostic interface - possibility to use both SW and HW traffic generators that support snappi API;
- fully dockerized environment;


SAI Challenger can be executed in two modes:
1. [standalone mode](docs/standalone_mode.md) - both syncd and pytest are running in the same Docker container;

<a href="url"><img src="img/sai-challenger-sm.svg" align="center" width="800" ></a>

2. [client-server mode](docs/client_server_mode.md) - syncd and pytest are running in the separate Docker containers;

<a href="url"><img src="img/sai-challenger-cs.svg" align="center" width="800" ></a>

The standalone mode **SHOULD** be used in case of:
- running TCs on vslib SAI implementation;
- running TCs without traffic (without `--traffic` option) on HW;
- running TCs with/without traffic on ASIC simulator when it also runs inside the same Docker container as syncd or sai_thrift server;

The client-server mode **CAN** be used in all the cases defined for the standalone mode, and **MUST** be used in case of:
- running TCs with traffic (with `--traffic` option) on HW;
- running TCs with traffic on ASIC simulator when it also runs inside the same Docker container as syncd or sai_thrift server but exposes ports outside the container;

## SAI Challenger sources

To get SAI Challenger sources:
```sh
git clone https://github.com/opencomputeproject/SAI-Challenger.git
cd sai-challenger/
git submodule update --init --recursive
```

# Architecture

- [Overview](./docs/architecture.md)
- [SAI client APIs](./docs/sai_clients.md)
- [SAI clients GET specification](./docs/client_attrs_spec.md)

# User guides

## Running tests

- [Composing testbed definition](./docs/testbed_definition.md)
- [Running tests in client-server mode](./docs/client_server_mode.md)
- [Running tests in standalone mode](./docs/standalone_mode.md).

## Porting SAI Challenger to new platform

For more information on how port SAI Challenger to new platform, please refer to [Porting Guide](docs/porting_guide.md) document.

## SAI Challenger internals

For more information on how SAI Challenger operates on SAI, please refer to [SAI operation](docs/sai_operation.md) document.


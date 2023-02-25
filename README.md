# SAI Challenger
SAI testing and integration framework for any SAI oriented devices. The main ideas behind SAI-Challenger are:
- testbed agnostic test cases - test case code does not require any changes for running in any type of environment - HW, emulation, different test equipment, links, servers, etc.;
- decoupling real SAI RPC implementation from test cases code - test code looks similar for configuring device using Thrift, Redis, etc.;
- traffic generator agnostic interface - possibility to use both SW and HW traffic generators that support snappi API;
- fully dockerized environment;


## SAI Challenger sources

To get SAI Challenger sources:
```sh
git clone https://github.com/opencomputeproject/SAI-Challenger.git
cd sai-challenger/
git submodule update --init --recursive
```
# Applications
SAI Challenger has many applications. A partial list is below:
* Virtual and Physical testbeds
* Testing and debugging libsai using saithrift, independent of any Network Operating System (NOS)
* SONiC-SAI Integration and test using sairedis
* CI/CD and regression testing of virtual or physical DUTs
* DUT performance testing using HW traffic generators
* PHY (transceiver) device testing & qualification
* Ubrella test harness for native SAI Challenger test cases as well as legacy SAI-PTF test cases, using a single-pane-of-glass to reduce testbed complexity.

# Use-case scenarios
SAI Challenger has many configuration options, resulting in numerous permutations of:
* Physical or virtual DUT testing
* DUT Configuration APIs - saithrift or sairedis
* Dataplane (packet test) - PTF/Scapy or OTG/snappi.

See [Use-Cases README](usecases/README.md) for more details. 

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


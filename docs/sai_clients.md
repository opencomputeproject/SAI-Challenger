## Objective

Sai-Challenger allows to apply SAI based configuration using multiple different APIs/PRC.
To achieve this a new sai_client entity is introduced to the architecture design.
Main point of the new design:
* SAI commands should be defined in _unified format_ that any sai_client can parse
* Each sai_client parses _unified_ SAI API calls and transforms them to the required by RPC form
* All tests use _unified_ SAI commands format. Switching between different sai_clients should not require changes in the test case code.
* User can easily switch between sai_clients in testbed configuration file

## High-level overview

On the picture below "SAI config" is a new __unified SAI format__ that is used in the test cases.
To run the test, user has to provide SAI client specific configuration ("SAI client config") that may depend on certain implementation. This configuration is a part of the standard testbed definition (see "JSON testbed definition" [TODO]).
SAI-Challenger core will redirect SAI config to an appropriate SAI client based on the SAI client configuration.

<a href="url"><img src="../img/SAI-Challenger HL.svg" align="center" width="800" ></a>

At this stage SAI-Challenger supports 2 SAI clients:
1. Redis
2. SAI-Thrift

But it is possible to add any custom SAI client.

## Implementation notes

### Class diagram

<a href="url"><img src="../img/SAI-Challenger class diagram.svg" align="center" width="800" ></a>

### Files/Folders

SAI clients root:
```sh
common/
└── sai_client
    ├── sai_redis_client [Redis client implementation]
    │── sai_thrift_client [Thrift client implementation]
    └── sai_client.py [Interface class]

```

### Adding new SaiClient
To add new SaiClient implementation - just inherit it from `saichallenger.common.sai_client.sai_client.SaiClient` and
implement it's abstract methods. After that register it at `SaiClient.build`. If you have to use your own SaiClient config -
see section below

## Test run flow

Typical test execution happen in the next manner
* pytest starts and get paths to test framework configurations
* configurations are passed to sai_environment.py setup script
* sai_environment.py loads accessible implementations and forms test environment model
  * configuration could include appliances of different types, every of which could be setup with its own API
  * traffic also could be sent and validated using various traffic generators
* SAI client initializes
* SAI configuration loads to the DUT using selected SAI API/RPC
* Dataplane manages traffic load

In the above schema SAI class doesn't have to know anything about low-level SAI API and because of this DUT could
be configured using same commands via different API backends. BTW: It's possible to use low-level SAI API itself, and SAI-Challenger grants such
possibility, but in this case portability to use different SAI backends for same test would be lost.

### SAI client config

SAI client configuration is a part of the JSON testbed definition from the "setup" folder.
Typical configuration of SaiThriftClient:

Example of the SAI Thrift configuration:
```json5
{
  "DPU": [
    {
      // ...
      "client": {
        "type": "thrift",
        "config": {
          "ip": "127.0.0.1",
          "port": "9092"
        }
      },
      // ...
    }
  ],
  //...
}
```

Example of the Redis configuration:
```json5
{
  "DPU": [
    {
      // ...
        "client": {
        "type": "redis",
        "config": {
            "ip": "172.17.0.3",
            "port": "6379",
            "loglevel": "DEBUG"
          }
      },
      // ...
    }
  ],
  //...
}
```

If you have implemented your own SaiClient:
1. Add new `type` to config
1. Assure that you have registered SaiClient in sai_client.py with same name at `SaiClient.build` method

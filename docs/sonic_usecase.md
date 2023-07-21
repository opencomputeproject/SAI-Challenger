## SONiC use-case

This document describes how to use a target device running SONiC NOS as a SAI DUT.

NOTE: In this operational mode, SAI Challenger utilizes Redis as an interface for SAI configuration, eliminating the need for any additional packages or applications to be built and deployed in the SONiC environment.

<a href="url"><img src="../img/sonic-dut.svg" align="center" width="700" ></a>
<br/><br/>

### Prepare SONiC device to be used as a SAI DUT

1. Make sure all SONiC services are up and running for more then 5 mins.
2. Make sure SAI Challenger uses the same SAI version (see [sai.env](../sai.env)) as it is used by the deployed SONiC image.
3. Check SONiC mgmt IP address

### Prepare testbed desciption file

Typical content of the testbed description file:
```sh
{
    "npu": [
      {
        "alias": "sonic-1",
        "asic": "generic",
        "target": null,
        "sku": null,
        "client": {
          "type": "redis",
          "config": {
            "mode": "sonic",
            "username": "admin",
            "password": "YourPaSsWoRd",
            "ip": "192.168.122.25",
            "port": "6379",
            "loglevel": "NOTICE"
          }
        }
      }
    ]
}
```

There are two configuration modes (`client.config.mode`):

**sonic** - in this mode, SAI Challenger stops all SONiC services, starts `database` and `syncd` services, and then executes specified test cases. SONiC state will not be restored after the test cases execution. This mode `SHOULD` be used in case multiple runs of the test cases is planned to be performed or SAI Challenger CLI is planned to be used.

**sonic-restore** - in this mode, SAI Challenger stops all SONiC services, starts `database` and `syncd` services, and then executes specified test cases. SONiC state will be restored right after the test cases execution. This mode `SHOULD` be used in case a single run of the test cases is planned and it is expected that SONiC will be up and running afterwards.

For more information on the testbed definition, please refer to [testbed_definition.md](testbed_definition.md) file.

### SAI Challenger build steps

Build SAI Challenger client Docker image with SAI Redis RPC.
```sh
./build.sh -i client
```

Spawn SAI Challenger client Docker container
```sh
./run.sh -i client
```

### Run SAI Challanger test cases

Run the test cases by specify a testbed name and pytest filter for the test cases
```sh
./exec.sh -i client pytest -v --testbed=sainpu_sonic -k "test_switch_ut"
```

### Run SAI Challanger CLI

Enter SAI Challenger runtime environment
```sh
./exec.sh -i client bash
```

Specify SAI testbed to use by the CLI
```sh
sai testbed set sainpu_sonic
```

List supported SAI object
```sh
sai list
```

List created SAI port objects
```sh
sai list port
```

Dump SAI port object state
```sh
sai dump oid:0x1000000000001
```

### Generic recommendations

During SAI Challenger execution:

1. Monitor SONiC services state
```sh
watch docker ps -a
```

2. Monitor errors in SONiC syslog
```sh
sudo tail -F /var/log/syslog
```


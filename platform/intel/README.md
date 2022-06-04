## Running SAI Challenger in standalone mode

Copy Debian packages `bfnsdk_1.0.0_amd64.deb` and `bfnplatform_1.0.0_amd64.deb` with Intel SDK and Tofino Model into `platform/intel/tofino/model/` folder.

Build Docker image for ASIC `tofino` target `model`:
```sh
./build.sh -a tofino -t model
```

Start Docker container in `--privileged` mode:
```sh
./run.sh -a tofino -t model -p
```

Run SAI Challenger testcases:
```sh
./exec.sh -a tofino -t model pytest --sku=32x25g --traffic -v -k "test_l2_basic"
```


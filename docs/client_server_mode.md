## Running SAI Challenger in client-server mode

Build client Docker image
```sh
./build.sh -i client
```

Build server Docker image for ASIC `trident2` target `saivs`:
```sh
./build.sh -i server -a trident2 -t saivs
```

Start SAI Challenger client:
```sh
./run.sh -i client
```

Start SAI Challenger server:
```sh
./run.sh -i server -a trident2 -t saivs
```

Run SAI Challenger testcases:
```sh
./exec.sh -i client pytest --asic trident2 --target saivs --sai-server=172.17.0.4 -v -k "test_l2_basic"
```

Run SAI Challenger testcases and generate HTML report:
```sh
./exec.sh -i client pytest --asic trident2 --target saivs --sai-server=172.17.0.4 -v -k "test_l2_basic" --html=report.html --self-contained-html
```

**NOTE:** The option `--traffic` will be ignored when running on `saivs` target.


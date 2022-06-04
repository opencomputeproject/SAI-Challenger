## Running SAI Challenger in standalone mode

Build Docker image for `trident2` ASIC for `saivs` target:
```sh
./build.sh -a trident2 -t saivs
```

**NOTE:** The `saivs` target - defined in sonic-sairedis - is used as a virtual data-plane interface in SONiC Virtual Switch (SONiC VS). Though it does not configure the forwarding path but still process SAI CRUD calls in proper manner. This allows to use `saivs` for SAI testcases development without running traffic.

Start Docker container:
```sh
./run.sh -a trident2 -t saivs
```

Run SAI Challenger testcases:
```sh
./exec.sh -a trident2 -t saivs pytest -v -k "test_l2_basic"
```

Run SAI Challenger testcases and generate HTML report:
```sh
./exec.sh -a trident2 -t saivs pytest -v -k "test_l2_basic" --html=report.html --self-contained-html
```


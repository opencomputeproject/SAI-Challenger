# Running PTF tests using SAI Challenger 

SAI has a rich collection of tests that is located at https://github.com/opencomputeproject/SAI/tree/master/ptf.
SAI Challenger has capability to run these tests by setting up proper test environment with SAI Thrift API and tests included. To run SAI PTF testcases, please follow the steps below.


# Steps to run tests

1. Setup the environment
```
git submodule update --init
```

2. Build a Docker image with a required test environment.
   This step is optional. The image can be implicitly pulled from DockerHub by `run.sh`.
```
./build.sh -s thrift
```

3. Start a Docker container
```
./run.sh -s thrift
```

4. Run a test


## Via pyTest

To run PTF test case:
```
pytest --testbed=saivs_thrift_standalone ../usecases/sai-ptf/SAI/ptf/saifdb.py -k FdbAttributeTest -v
```

To run SAI Challenger test case using Thrift RPC:
```
pytest --testbed=saivs_thrift_standalone -k "access_to_access" -v
```

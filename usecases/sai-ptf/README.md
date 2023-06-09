# Running PTF tests using SAI Challenger 

SAI has a rich collection of tests that is located at https://github.com/opencomputeproject/SAI/tree/master/ptf.
SAI Challenger has capability to run these tests by setting up proper test environment with SAI Thrift API and tests included. To run SAI PTF testcases, please follow the steps below.


# Steps to run tests

0. Setup the environment
```
git submodule update --init
cp usecases/sai-ptf/ptf-conftest.py usecases/sai-ptf/SAI/ptf/conftest.py
cp usecases/sai-ptf/patches/0001-sai-base-test.patch usecases/sai-ptf/SAI/
cd usecases/sai-ptf/SAI/ && patch -p1 < 0001-sai-base-test.patch && cd -
```

1. Build a Docker image with required test env
```
./build.sh -s thrift
```

2. Start a container based on newly built image
```
./run.sh -s thrift
```

3. Login into the container
```
docker exec -ti sc-thrift-trident2-saivs-run bash
```

4. Run a test


## Via pyTest

To run PTF test case:
```
pytest --testbed=saivs_thrift_standalone ../usecases/sai-ptf/SAI/ptf/saifdb.py -k FdbAttributeTest -v
```

To clean-up `saiserver` for `saivs` target after test case execution:
```
supervisorctl restart saiserver
```

To run SAI Challenger test case using Thrift RPC:
```
pytest --testbed=saivs_thrift_standalone -k "access_to_access" -v
```

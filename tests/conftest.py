import os
import pytest
import sys

curdir = os.path.dirname(os.path.realpath(__file__))
commondir = os.path.join(curdir, '../common')
sys.path.append(commondir)

from sai_npu import SaiNpu
from sai_testbed import SaiTestbed


def pytest_addoption(parser):
    parser.addoption("--sai-server", action="store", default='localhost', help="SAI server IP")
    parser.addoption("--traffic", action="store_true", default=False, help="run tests with traffic")
    parser.addoption("--saivs", action="store_true", default=False, help="running tests on top of libsaivs")
    parser.addoption("--loglevel", action="store", default='NOTICE', help="syncd logging level")
    parser.addoption("--asic", action="store", default=os.getenv('SC_ASIC'), help="ASIC type")
    parser.addoption("--target", action="store", default=os.getenv('SC_TARGET'), help="The target device with this NPU")
    parser.addoption("--sku", action="store", default=None, help="SKU mode")
    parser.addoption("--testbed", action="store", default=None, help="Testbed name")


@pytest.fixture(scope="session")
def exec_params(request):
    config_param = {}
    config_param["mgmt_ip"] = request.config.getoption("--sai-server")
    config_param["traffic"] = request.config.getoption("--traffic")
    config_param["saivs"] = request.config.getoption("--saivs")
    config_param["loglevel"] = request.config.getoption("--loglevel")
    config_param["asic"] = request.config.getoption("--asic")
    config_param["target"] = request.config.getoption("--target")
    config_param["sku"] = request.config.getoption("--sku")
    config_param["testbed"] = request.config.getoption("--testbed")
    return config_param


@pytest.fixture(scope="session")
def testbed_instance(exec_params):
    testbed_name = exec_params.get("testbed", None)
    if testbed_name is None:
        yield None
    else:
        testbed = SaiTestbed(testbed_name)
        testbed.init()
        yield testbed
        testbed.deinit()


@pytest.fixture(scope="function")
def testbed(testbed_instance):
    if testbed_instance:
        testbed_instance.setup()
        yield testbed_instance
        testbed_instance.teardown()
    else:
        yield None


@pytest.fixture(scope="session")
def npu(exec_params, testbed_instance):
    testbed_name = exec_params.get("testbed", None)
    if testbed_instance is not None:
        if len(testbed_instance.dut) > 1:
            return None
        return testbed_instance.dut[0]

    npu = None
    exec_params["asic_dir"] = None

    if exec_params["asic"] == "generic":
        npu = SaiNpu(exec_params)
    else:
        npu = SaiTestbed.spawn_npu(exec_params)

    if npu is not None:
        npu.reset()
    return npu


@pytest.fixture(scope="session")
def dataplane_instance(exec_params, testbed_instance):
    if testbed_instance is not None:
        if len(testbed_instance.dataplane) > 1:
            yield None
        else:
            yield testbed_instance.dataplane[0]
    else:
        dp = SaiTestbed.spawn_dataplane(exec_params)
        dp.init()
        yield dp
        dp.deinit()


@pytest.fixture(scope="function")
def dataplane(dataplane_instance):
    if dataplane_instance:
        dataplane_instance.setup()
        yield dataplane_instance
        dataplane_instance.teardown()
    else:
        yield None

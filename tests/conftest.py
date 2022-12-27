import os
import pytest

curdir = os.path.dirname(os.path.realpath(__file__))

from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_testbed import SaiTestbed


def pytest_addoption(parser):
    parser.addoption("--sai-server", action="store", default='localhost', help="SAI server IP")
    parser.addoption("--traffic", action="store_true", default=False, help="run tests with traffic")
    parser.addoption("--loglevel", action="store", default='NOTICE', help="syncd logging level")
    parser.addoption("--asic", action="store", default=os.getenv('SC_ASIC'), help="ASIC type")
    parser.addoption("--target", action="store", default=os.getenv('SC_TARGET'), help="The target device with this NPU")
    parser.addoption("--sku", action="store", default=None, help="SKU mode")
    parser.addoption("--testbed", action="store", default=None, help="Testbed name")


@pytest.fixture(scope="session")
def exec_params(request):
    config_param = {
        # Generic parameters
        "traffic": request.config.getoption("--traffic"),
        "testbed": request.config.getoption("--testbed"),
        # DUT specific parameters
        "alias": "dut",
        "asic": request.config.getoption("--asic"),
        "target": request.config.getoption("--target"),
        "sku": request.config.getoption("--sku"),
        "client": {
            "type": "redis",
            "config": {
                "ip": request.config.getoption("--sai-server"),
                "port": "6379",
                "loglevel": request.config.getoption("--loglevel")
            }
        }
    }
    return config_param


@pytest.fixture(scope="session")
def testbed_instance(exec_params):
    testbed_name = exec_params.get("testbed", None)
    if testbed_name is None:
        yield None
    else:
        testbed = SaiTestbed(f"{curdir}/..", testbed_name, exec_params["traffic"])
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
    if testbed_instance is not None:
        if len(testbed_instance.npu) == 1:
            return testbed_instance.npu[0]
        return None

    npu = None
    exec_params["asic_dir"] = None

    if exec_params["asic"] == "generic":
        npu = SaiNpu(exec_params)
    else:
        npu = SaiTestbed.spawn_asic(f"{curdir}/..", exec_params, "npu")

    if npu is not None:
        npu.reset()
    return npu


@pytest.fixture(scope="session")
def dpu(exec_params, testbed_instance):
    if testbed_instance is not None:
        if len(testbed_instance.dpu) == 1:
            return testbed_instance.dpu[0]
        return None

    dpu = None
    exec_params["asic_dir"] = None

    if exec_params["asic"] == "generic":
        dpu = SaiDpu(exec_params)
    else:
        dpu = SaiTestbed.spawn_asic(f"{curdir}/..", exec_params, "dpu")

    if dpu is not None:
        dpu.reset()
    return dpu


@pytest.fixture(scope="session")
def dataplane_instance(testbed_instance):
    if testbed_instance is not None:
        if len(testbed_instance.dataplane) > 1:
            yield None
        else:
            yield testbed_instance.dataplane[0]
    else:
        dp = SaiTestbed.spawn_dataplane({"type": "ptf"})
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

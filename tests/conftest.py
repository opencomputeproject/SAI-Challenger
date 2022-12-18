import logging
import os
import sys
import pytest
from saichallenger.common.sai_environment import init_setup

curdir = os.path.dirname(os.path.realpath(__file__))
commondir = os.path.join(curdir, '../common')
sys.path.append(commondir)


def pytest_addoption(parser):
    parser.addoption("--traffic", action="store_true", default=False, help="run tests with traffic")
    parser.addoption("--loglevel", action="store", default='NOTICE', help="syncd logging level")
    parser.addoption("--setup", action="store", default=None, help="Setup description (Path to the json file).")


@pytest.fixture(scope="session")
def exec_params(request):
    config_param = {}
    config_param["setup"] = init_setup(request.config)
    config_param["server"] = "localhost"
    config_param["traffic"] = request.config.getoption("--traffic")
    config_param["loglevel"] = request.config.getoption("--loglevel")
    logging.getLogger().setLevel(getattr(logging, config_param["loglevel"].upper(), "INFO"))
    return config_param


@pytest.fixture(scope="session")
def npu(exec_params):
    npu = exec_params["setup"]["NPU"][0]
    if npu is not None:
        npu.reset()
    return npu


# NOTE: Obsoleted. The `npu` fixture should be used instead.
@pytest.fixture(scope="session")
def sai(npu):
    return npu


@pytest.fixture(scope="session")
def dataplane_session(exec_params):
    dataplane = exec_params["setup"]["DATAPLANE"][0]
    # Set up the dataplane
    dataplane.init()
    yield dataplane
    # Shutdown the dataplane
    dataplane.remove()


@pytest.fixture(scope="function")
def dataplane(dataplane_session):
    dataplane_session.setUp()
    yield dataplane_session
    dataplane_session.tearDown()

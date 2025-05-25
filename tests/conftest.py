import os
import pytest

curdir = os.path.dirname(os.path.realpath(__file__))

from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_phy import SaiPhy
from saichallenger.common.sai_testbed import SaiTestbed
from saichallenger.common.sai_data import SaiObjType

_previous_test_failed = False
_last_failed_context = None
_previous_test_context = None
_current_test_context = None
_module_failed = {}

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    '''
    This code defines a hook, which is executed after each phase
    of a test execution and is responsible for creating a test report.

    The "when" attribute of the test report represents the phase of the test:
      - "setup": the report is generated during the setup phase of the test.
      - "call": the report is generated during the actual execution of the test.
      - "teardown": the report is generated during the teardown phase of the test.

    The outcome of a test can have the following possible values:
      - "passed": the test has passed successfully.
      - "failed": the test has failed.
      - "skipped": the test was skipped intentionally.
      - "error": an unexpected error occurred during the test execution.
      - "xfailed": the test was expected to fail, and it actually failed as expected.
      - "xpassed": the test was expected to fail, but it passed unexpectedly.
    '''

    outcome = yield
    rep = outcome.get_result()

    global _previous_test_failed
    if rep.when == "setup":
        # Store initial outcome of the test
        _previous_test_failed = rep.outcome not in ["passed", "skipped"]
    elif not _previous_test_failed:
        # Update the outcome only in case all previous phases were successful
        _previous_test_failed = rep.outcome not in ["passed", "skipped"]

    global _last_failed_context

    if rep.when == "call" and rep.failed:
        module_name = item.module.__name__
        _last_failed_context = module_name
        _module_failed[module_name] = True


@pytest.fixture
def prev_test_failed():
    global _previous_test_failed
    return _previous_test_failed


@pytest.fixture(scope="module", autouse=True)
def track_context(request):
    global _current_test_context
    global _previous_test_context
    global _last_failed_context

    _previous_test_context = _current_test_context
    _current_test_context = request.module.__name__

    if _previous_test_context != _last_failed_context:
        _last_failed_context = None


@pytest.fixture(scope="module")
def prev_context_failed(track_context):
    global _last_failed_context, _current_test_context
    return _last_failed_context is not None and _last_failed_context != _current_test_context


def has_module_failed(request, clear_on_read=False):
    if clear_on_read:
        global _last_failed_context
        _last_failed_context = None
    return _module_failed.get(request.module.__name__, False)


def pytest_addoption(parser):
    parser.addoption("--traffic", action="store_true", help="run tests with traffic")
    parser.addoption("--testbed", action="store", help="Testbed name", required=True)


def pytest_sessionstart(session):
    SaiObjType.generate_from_thrift()
    SaiObjType.generate_from_json()


@pytest.fixture(scope="session")
def exec_params(request):
    config_param = {
        # Generic parameters
        "traffic": request.config.getoption("--traffic"),
        "testbed": request.config.getoption("--testbed"),
    }
    return config_param


@pytest.fixture(scope="session")
def testbed_instance(exec_params):
    testbed = SaiTestbed(f"{curdir}/..", exec_params["testbed"], exec_params["traffic"])
    testbed.init()
    yield testbed
    testbed.deinit()


@pytest.fixture(scope="function")
def testbed(testbed_instance):
    testbed_instance.setup()
    yield testbed_instance
    testbed_instance.teardown()


@pytest.fixture(scope="session")
def npu(testbed_instance):
    if len(testbed_instance.npu) == 1:
        return testbed_instance.npu[0]
    return None


@pytest.fixture(scope="session")
def dpu(testbed_instance):
    if len(testbed_instance.dpu) == 1:
        return testbed_instance.dpu[0]
    return None


@pytest.fixture(scope="session")
def phy(testbed_instance):
    if len(testbed_instance.phy) == 1:
        return testbed_instance.phy[0]
    return None


@pytest.fixture(scope="session")
def dataplane_instance(testbed_instance):
    if len(testbed_instance.dataplane) == 1:
        yield testbed_instance.dataplane[0]
    else:
        yield None


@pytest.fixture(scope="function")
def dataplane(dataplane_instance):
    if dataplane_instance:
        dataplane_instance.setup()
        yield dataplane_instance
        dataplane_instance.teardown()
    else:
        yield None

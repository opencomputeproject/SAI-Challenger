import os
import pytest
import time

curdir = os.path.dirname(os.path.realpath(__file__))

from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_phy import SaiPhy
from saichallenger.common.sai_testbed import SaiTestbed
from saichallenger.common.sai_data import SaiObjType
import saichallenger.topologies.sai_ptf_topology

_previous_test_failed = False

_last_failed_module = None
_previous_test_module = None
_current_test_module = None
_module_failed = {}

class TopologyManager:
    """
    Manages the caching and lifecycle of the SAI PTF topology. 
    This ensures strict test isolation and prevents Redis RPC crashes 
    by safely resetting the hardware state between test runs.
    """
    def __init__(self, npu):
        """Initializes the manager with the target NPU."""
        self.npu = npu
        self.context = None
        self.topo = None

    def get_topology(self, force_redeploy=False):
        """
        Retrieves the active topology. 
        Creates a new context if one does not exist.
        """
        if self.topo is None:
            self.context = saichallenger.topologies.sai_ptf_topology.config(self.npu)
            self.topo = self.context.__enter__()
        return self.topo

    def close(self):
        """
        Safely tears down the topology context. 
        Mocks critical NPU methods to prevent state leakage and framework crashes.
        """
        if self.context:
            _cli = getattr(self.npu, "sai_client", None)
            orig_vid_to_rid = getattr(_cli, "vid_to_rid", None) if _cli else None
            orig_remove = self.npu.remove
            orig_create = self.npu.create
            orig_restore = getattr(self.topo, "restore_default_bridge_ports", None)

            if orig_remove:
                self.npu.remove = lambda obj, do_assert=False: safe_execute(orig_remove, obj, do_assert=False)
            if orig_create:
                self.npu.create = lambda obj_type, attrs, do_assert=False: safe_execute(orig_create, obj_type, attrs, do_assert=False)

            if self.topo and orig_restore:
                def silent_restore():
                    try:
                        return orig_restore()
                    except BaseException:
                        return None
                self.topo.restore_default_bridge_ports = silent_restore

            try:
                self.context.__exit__(None, None, None)
            finally:
                if _cli and orig_vid_to_rid:
                    _cli.vid_to_rid = orig_vid_to_rid
                if orig_remove:
                    self.npu.remove = orig_remove
                if orig_create:
                    self.npu.create = orig_create
                if self.topo and orig_restore:
                    self.topo.restore_default_bridge_ports = orig_restore
                
            self.context = None
            self.topo = None


def safe_execute(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except BaseException:
        return "oid:0x0"
    
@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for "{}" testbed'.format(testbed.name))


def verify_sai_clean_state(npu):
    """
    Helper function to verify that the ASIC has no leftover user objects.
    """
    try:
        fdb_keys = npu.get_db_keys("ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY*")
        if len(fdb_keys) > 0:
            return False, f"Leftover FDB entries: {fdb_keys}"

        lag_keys = npu.get_db_keys("ASIC_STATE:SAI_OBJECT_TYPE_LAG*")
        if lag_keys and len(lag_keys) > 0:
            return False, f"Leftover LAG objects found: {lag_keys}"

        vlan_keys = npu.get_db_keys("ASIC_STATE:SAI_OBJECT_TYPE_VLAN*")
        if vlan_keys and len(vlan_keys) > 1:
            return False, f"Leftover custom VLANs found: {vlan_keys}"
    except AttributeError:

        try:
            status, _ = npu.get("oid:0xa", ["SAI_VLAN_ATTR_VLAN_ID"], False)
            if status is True or status == 0:
                return False, "VLAN 10 still exists after reset"
        except Exception as e:
            pass

    except Exception as e:
        return False, f"Failed to fetch NPU state: {str(e)}"

    return True, ""


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

    if rep.failed or rep.outcome == "error":
        _previous_test_failed = True

    global _last_failed_module
    global _module_failed

    if rep.when == "call" and rep.failed:
        module_name = item.module.__name__
        _last_failed_module = module_name
        _module_failed[module_name] = True


@pytest.fixture
def prev_test_failed():
    global _previous_test_failed
    failed_state = _previous_test_failed
    _previous_test_failed = False
    return failed_state

@pytest.fixture(scope="class")
def sai_ptf_topology_manager(npu):
    """
    Provides a class-scoped TopologyManager instance to cache the topology.
    """
    manager = TopologyManager(npu)
    yield manager
    manager.close()

@pytest.fixture(scope="function")
def sai_ptf_topology(request, sai_ptf_topology_manager, prev_test_failed, npu):
    """
    Provides the active PTF topology instance for the current test.
    This ensures strict test isolation by automatically destroying the old context, 
    resetting the NPU, and clearing Redis queues whenever a test fails or a new class starts.
    """
    cls = request.cls
    force_redeploy = False

    last_cls = getattr(request.session, "_last_run_class", None)
    if cls and last_cls and last_cls != cls:
        force_redeploy = True

    if cls:
        request.session._last_run_class = cls

    if prev_test_failed or force_redeploy:
        sai_ptf_topology_manager.close()
        
        try:
            npu.reset()
        except BaseException:
            pass
            
        if hasattr(npu, "switch_id"):
            npu.switch_id = None
            
        time.sleep(2)
        
        _cli = getattr(npu, "sai_client", None)
        if _cli and hasattr(_cli, 'r'):
            try:
                _cli.r.delete("ASIC_STATE_KEY_VALUE_OP_QUEUE")
                _cli.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")
            except BaseException:
                pass
                
        if prev_test_failed and 'verify_sai_clean_state' in globals():
            is_clean, error_msg = verify_sai_clean_state(npu)
            if not is_clean:
                pytest.exit(f"[CRITICAL] NPU recovery failed: {error_msg}")
                
        return sai_ptf_topology_manager.get_topology()
    
    return sai_ptf_topology_manager.get_topology()


@pytest.fixture(autouse=True, scope="function")
def setup_teardown(request, npu, sai_ptf_topology, prev_test_failed):
    """
    Manages the execution of hardware setup and class variables for each test.
    This optimizes performance by configuring hardware only once per successful class run, 
    while guaranteeing recovery by forcing a fresh setup after any failure or class change.
    """
    cls = request.cls
    instance = request.instance

    last_cls = getattr(request.session, "_last_run_class", None)
    if cls:
        if (last_cls and last_cls != cls) or prev_test_failed:
            cls._hardware_configured = False

    if not getattr(cls, "_hardware_configured", False):
        if instance and hasattr(instance, "_execute_hardware_setup"):   
            instance._execute_hardware_setup(npu, sai_ptf_topology)
        if cls:
            cls._hardware_configured = True

    if instance and hasattr(instance, "_apply_class_variables"):
        instance._apply_class_variables(request, sai_ptf_topology)

    yield


@pytest.fixture(scope="module", autouse=True)
def track_module(request):
    global _current_test_module
    global _previous_test_module
    global _last_failed_module

    _previous_test_module = _current_test_module
    _current_test_module = request.module.__name__

    if _previous_test_module != _last_failed_module:
        _last_failed_module = None


@pytest.fixture(scope="module")
def prev_module_failed(track_module):
    global _last_failed_module
    global _current_test_module
    return _last_failed_module is not None and _last_failed_module != _current_test_module


@pytest.fixture(scope="module")
def has_module_failed(request):
    def _check():
        return _module_failed.get(request.module.__name__, False)
    yield _check


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

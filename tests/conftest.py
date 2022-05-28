import logging
import time
import pytest
import os
import sys
import imp
import signal
import random
import unittest
import glob

curdir = os.path.dirname(os.path.realpath(__file__))
ptfdir = os.path.join(curdir, '../ptf/src')
sys.path.append(ptfdir)

import ptf
from ptf import config
import ptf.ptfutils

commondir = os.path.join(curdir, '../common')
sys.path.append(commondir)

from sai_npu import SaiNpu
from sai_dataplane import SaiDataPlane


##@var DEBUG_LEVELS
# Map from strings to debugging levels
DEBUG_LEVELS = {
    'debug'              : logging.DEBUG,
    'verbose'            : logging.DEBUG,
    'info'               : logging.INFO,
    'warning'            : logging.WARNING,
    'warn'               : logging.WARNING,
    'error'              : logging.ERROR,
    'critical'           : logging.CRITICAL
}


# The default configuration dictionary for PTF
config_default = {
    # Miscellaneous options
    "list"               : False,
    "list_test_names"    : False,
    "allow_user"         : False,

    # Test selection options
    "test_spec"          : "",
    "test_file"          : None,
    "test_dir"           : None,
    "test_order"         : "default",
    "test_order_seed"    : 0xaba,

    # Switch connection options
    "platform"           : "eth",
    "platform_args"      : None,
    "platform_dir"       : None,
    "interfaces"         : [
                                (0,  0, "eth1"),
                                (0,  1, "eth2"),
                                (0,  2, "eth3"),
                                (0,  3, "eth4"),
                                (0,  4, "eth5"),
                                (0,  5, "eth6"),
                                (0,  6, "eth7"),
                                (0,  7, "eth8"),
                                (0,  8, "eth9"),
                                (0,  9, "eth10"),
                                (0, 10, "eth11"),
                                (0, 11, "eth12"),
                                (0, 12, "eth13"),
                                (0, 13, "eth14"),
                                (0, 14, "eth15"),
                                (0, 15, "eth16"),
                           ],
    "device_sockets"     : [],  # when using nanomsg

    # Logging options
    "log_file"           : "ptf.log",
    "log_dir"            : None,
    "debug"              : "verbose",
    "profile"            : False,
    "profile_file"       : "profile.out",
    "xunit"              : False,
    "xunit_dir"          : "xunit",

    # Test behavior options
    "relax"              : False,
    "test_params"        : None,
    "failfast"           : False,
    "fail_skipped"       : False,
    "default_timeout"    : 2.0,
    "default_negative_timeout" : 0.1,
    "minsize"            : 0,
    "random_seed"        : None,
    "disable_ipv6"       : False,
    "disable_vxlan"      : True,
    "disable_erspan"     : True,
    "disable_geneve"     : True,
    "disable_mpls"       : True,
    "disable_nvgre"      : True,
    "disable_igmp"       : False,
    "qlen"               : 100,
    "test_case_timeout"  : None,

    # Socket options
    "socket_recv_size"   : 4096,

    # Other configuration
    "port_map"           : None,
}

def pytest_addoption(parser):
    parser.addoption("--sai-server", action="store", default='localhost', help="SAI server IP")
    parser.addoption("--traffic", action="store_true", default=False, help="run tests with traffic")
    parser.addoption("--saivs", action="store_true", default=False, help="running tests on top of libsaivs")
    parser.addoption("--loglevel", action="store", default='NOTICE', help="syncd logging level")
    parser.addoption("--asic", action="store", default='BCM56850', help="ASIC type")
    parser.addoption("--target", action="store", default='', help="The target device with this NPU")
    parser.addoption("--sku", action="store", default=None, help="SKU mode")


@pytest.fixture(scope="session")
def exec_params(request):
    config_param = {}
    config_param["server"] = request.config.getoption("--sai-server")
    config_param["traffic"] = request.config.getoption("--traffic")
    config_param["saivs"] = request.config.getoption("--saivs")
    config_param["loglevel"] = request.config.getoption("--loglevel")
    config_param["asic"] = request.config.getoption("--asic")
    config_param["target"] = request.config.getoption("--target")
    config_param["sku"] = request.config.getoption("--sku")
    return config_param


def logging_setup(config):
    """
    Set up logging based on config
    """

    logging.getLogger().setLevel(DEBUG_LEVELS[config["debug"]])

    if config["log_dir"] != None:
        if os.path.exists(config["log_dir"]):
            import shutil
            shutil.rmtree(config["log_dir"])
        os.makedirs(config["log_dir"])
    else:
        if os.path.exists(config["log_file"]):
            os.remove(config["log_file"])

    ptf.open_logfile('main')


@pytest.fixture(scope="session")
def npu(exec_params):
    npu = None
    exec_params["asic_dir"] = None

    if exec_params["asic"] == "generic":
        npu = SaiNpu(exec_params)
    else:
        asic_dir = None
        npu_mod = None
        module_name = "sai_npu"

        try:
            asic_dir = glob.glob("../platform/**/" + exec_params["asic"] + "/", recursive=True)
            asic_dir = asic_dir[0]
            exec_params["asic_dir"] = asic_dir
        except:
            logging.critical("Failed to find " + exec_params["asic"] + " NPU folder")
            sys.exit(1)

        try:
            npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir]))
        except:
            logging.info("No {} specific 'sai_npu' module defined..".format(exec_params["asic"]))
            try:
                npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir + "../"]))
            except:
                logging.warn("No platform specific 'sai_npu' module defined..")

        if npu_mod is not None:
            try:
                npu = npu_mod.SaiNpuImpl(exec_params)
            except:
                logging.critical("Failed to instantiate 'sai_npu' module for {}".format(exec_params["asic"]))
                sys.exit(1)
        else:
            logging.info("Falling back to the default 'sai_npu' module..")
            npu = SaiNpu(exec_params)

    if npu is not None:
        npu.reset()
    return npu


# NOTE: Obsoleted. The `npu` fixture should be used instead.
@pytest.fixture(scope="session")
def sai(npu):
    return npu


@pytest.fixture(scope="session")
def dataplane_init():
    global ptf
    ptf.config.update(config_default)

    logging_setup(config)

    logging.info("++++++++ " + time.asctime() + " ++++++++")

    # import after logging is configured so that scapy error logs (from importing
    # packet.py) are silenced and our own warnings are logged properly.
    import ptf.testutils

    if config["platform_dir"] is None:
        from ptf import platforms
        config["platform_dir"] = os.path.dirname(os.path.abspath(platforms.__file__))

    # Allow platforms to import each other
    sys.path.append(config["platform_dir"])

    # Load the platform module
    platform_name = config["platform"]
    logging.info("Importing platform: " + platform_name)

    if platform_name == "nn":
        try:
            import nnpy
        except:
            logging.critical("Cannot use 'nn' platform if nnpy package is not installed")
            sys.exit(1)

    platform_mod = None
    try:
        platform_mod = imp.load_module(platform_name, *imp.find_module(platform_name, [config["platform_dir"]]))
    except:
        logging.warn("Failed to import " + platform_name + " platform module")
        raise

    try:
        platform_mod.platform_config_update(config)
    except:
        logging.warn("Could not run platform host configuration")
        raise

    if config["port_map"] is None:
        logging.critical("Interface port map was not defined by the platform. Exiting.")
        sys.exit(1)

    logging.debug("Configuration: " + str(config))
    logging.info("port map: " + str(config["port_map"]))

    ptf.ptfutils.default_timeout = config["default_timeout"]
    ptf.ptfutils.default_negative_timeout = config["default_negative_timeout"]
    ptf.testutils.MINSIZE = config['minsize']

    if os.getuid() != 0 and not config["allow_user"] and platform_name != "nn":
        logging.critical("Super-user privileges required. Please re-run with sudo or as root.")
        sys.exit(1)

    if config["random_seed"] is not None:
        logging.info("Random seed: %d" % config["random_seed"])
        random.seed(config["random_seed"])
    else:
        # Generate random seed and report to log file
        seed = random.randrange(100000000)
        logging.info("Autogen random seed: %d" % seed)
        random.seed(seed)

    # Remove python's signal handler which raises KeyboardError. Exiting from an
    # exception waits for all threads to terminate which might not happen.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Set up the dataplane
    dataplane_instance = ptf.dataplane.DataPlane(config)
    if config["log_dir"] == None:
        filename = os.path.splitext(config["log_file"])[0] + '.pcap'
        dataplane_instance.start_pcap(filename)

    for port_id, ifname in config["port_map"].items():
        device, port = port_id
        dataplane_instance.port_add(ifname, device, port)

    logging.info("++++++++ " + time.asctime() + " ++++++++")

    yield dataplane_instance

    # Shutdown the dataplane
    dataplane_instance.stop_pcap()
    dataplane_instance.kill()


@pytest.fixture(scope="function")
def dataplane(dataplane_init):
    dataplane = SaiDataPlane(dataplane_init)
    dataplane.setUp()

    yield dataplane

    dataplane.tearDown()

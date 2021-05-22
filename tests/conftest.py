import logging
import time
import pytest
from common.switch import Sai
import os
import sys
import imp
import signal
import random
import unittest

curdir = os.path.dirname(os.path.realpath(__file__))
ptfdir = os.path.join(curdir, '../ptf/src')
sys.path.append(ptfdir)

import ptf
from ptf import config
import ptf.ptfutils


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
    parser.addoption("--sai-server", action="store", default='localhost')


@pytest.fixture(scope="session")
def sai_server(request):
    return request.config.getoption("--sai-server")


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


def pcap_setup(config):
    """
    Set up dataplane packet capturing based on config
    """

    if config["log_dir"] == None:
        filename = os.path.splitext(config["log_file"])[0] + '.pcap'
        ptf.dataplane_instance.start_pcap(filename)
    else:
        # start_pcap is called per-test in base_tests
        pass


@pytest.fixture(scope="session")
def sai(sai_server):
    sai = Sai(sai_server)
    return sai


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
            die("Cannot use 'nn' platform if nnpy package is not installed")

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
        die("Interface port map was not defined by the platform. Exiting.")

    logging.debug("Configuration: " + str(config))
    logging.info("port map: " + str(config["port_map"]))

    ptf.ptfutils.default_timeout = config["default_timeout"]
    ptf.ptfutils.default_negative_timeout = config["default_negative_timeout"]
    ptf.testutils.MINSIZE = config['minsize']

    if os.getuid() != 0 and not config["allow_user"] and platform_name != "nn":
        die("Super-user privileges required. Please re-run with sudo or as root.")

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
    ptf.dataplane_instance = ptf.dataplane.DataPlane(config)
    pcap_setup(config)
    for port_id, ifname in config["port_map"].items():
        device, port = port_id
        ptf.dataplane_instance.port_add(ifname, device, port)

    logging.info("++++++++ " + time.asctime() + " ++++++++")

    yield

    # Shutdown the dataplane
    ptf.dataplane_instance.stop_pcap()  # no-op is pcap not started
    ptf.dataplane_instance.kill()
    ptf.dataplane_instance = None


class DataplaneBase(unittest.TestCase):
    def __init__(self):
        pass

    def setUp(self):
        self.dataplane = ptf.dataplane_instance
        self.dataplane.flush()
        if config["log_dir"] != None:
            filename = os.path.join(config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def before_send(self, pkt, device_number=0, port_number=-1):
        pass

    def at_receive(self, pkt, device_number=0, port_number=-1):
        pass

    def tearDown(self):
        if config["log_dir"] != None:
            self.dataplane.stop_pcap()

@pytest.fixture(scope="function")
def dataplane(dataplane_init):
    dataplane = DataplaneBase()
    dataplane.setUp()

    yield dataplane

    dataplane.tearDown()



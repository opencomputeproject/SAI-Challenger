import imp
import logging
import os
import random
import signal
import sys
import time

import ptf.ptfutils
from ptf import config

from sai_dataplane import SaiDataplane


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
    "interfaces"         : [],
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


class SaiDataplaneImpl(SaiDataplane):

    def __init__(self, exec_params):
        super().__init__(exec_params)
        self.alias = exec_params['alias']

    def _build_interfaces(self):
        interfaces = []
        for port in self.port_instances:
            interfaces.append((0, port.id, port.alias))
        return interfaces

    def init(self):
        global ptf
        ptf.config.update(config_default)
        logging_setup(config)

        ptf.config['interfaces'] = self._build_interfaces()

        ptf.open_logfile('main')

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

        dataplane_instance = ptf.dataplane.DataPlane(config)

        if config["log_dir"] == None:
            filename = os.path.splitext(config["log_file"])[0] + '.pcap'
            dataplane_instance.start_pcap(filename)

        for port_id, ifname in config["port_map"].items():
            device, port = port_id
            dataplane_instance.port_add(ifname, device, port)

        logging.info("++++++++ " + time.asctime() + " ++++++++")

        self.dataplane = dataplane_instance

    def remove(self):
        self.dataplane.stop_pcap()
        self.dataplane.kill()

    def setUp(self):
        super().setUp()
        self.dataplane.flush()
        if config["log_dir"] != None:
            filename = os.path.join(config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def tearDown(self):
        super().tearDown()
        if config["log_dir"] != None:
            self.dataplane.stop_pcap()

    def getPortMap(self):
        return config["port_map"]

    def setPortMap(self, port_map):
        config["port_map"] = port_map

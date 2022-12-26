import ptf
import ptf.dataplane
from ptf import config
from unittest import TestCase
import os
import copy
import sys
import imp
import random
import time
import signal
import logging
from sai_dataplane.sai_dataplane import SaiDataPlane


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
                                (0,  0, "veth1"),
                                (0,  1, "veth2"),
                                (0,  2, "veth3"),
                                (0,  3, "veth4"),
                                (0,  4, "veth5"),
                                (0,  5, "veth6"),
                                (0,  6, "veth7"),
                                (0,  7, "veth8"),
                                (0,  8, "veth9"),
                                (0,  9, "veth10"),
                                (0, 10, "veth11"),
                                (0, 11, "veth12"),
                                (0, 12, "veth13"),
                                (0, 13, "veth14"),
                                (0, 14, "veth15"),
                                (0, 15, "veth16"),
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


class SaiPtfDataPlane(SaiDataPlane, TestCase):
    def __init__(self, cfg=None):
        super().__init__(cfg)

    def setUp(self):
        assert self.dataplane is not None
        self.dataplane.flush()
        if config["log_dir"] != None:
            filename = os.path.join(config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def before_send(self, pkt, device_number=0, port_number=-1):
        pass

    def at_receive(self, pkt, device_number=0, port_number=-1):
        pass

    def tearDown(self):
        assert self.dataplane is not None
        if config["log_dir"] != None:
            self.dataplane.stop_pcap()

    @staticmethod
    def getPortMap():
        return config["port_map"]

    @staticmethod
    def setPortMap(port_map):
        config["port_map"] = port_map

    @staticmethod
    def __logging_setup(config):
        """
        Set up logging based on config
        """

        DEBUG_LEVELS = {
            'debug'              : logging.DEBUG,
            'verbose'            : logging.DEBUG,
            'info'               : logging.INFO,
            'warning'            : logging.WARNING,
            'warn'               : logging.WARNING,
            'error'              : logging.ERROR,
            'critical'           : logging.CRITICAL
        }

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

    def init(self):
        global ptf
        ptf.config.update(config_default)

        self.__logging_setup(config)

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

        if self.config and (self.config.get("port_groups", None) is not None):
            device = 0
            port_map = {}
            for port in self.config.get("port_groups"):
                port_map[(device, port["alias"])] = port["name"]
            config["port_map"] = port_map
        else:
            try:
                platform_mod.platform_config_update(config)
            except:
                logging.warn("Could not run platform host configuration")
                raise

        if config["port_map"] is None:
            #logging.critical("Interface port map was not defined by the platform. Exiting.")
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

        self.dataplane = dataplane_instance

    def deinit(self):
        if self.dataplane is not None:
            self.dataplane.stop_pcap()
            self.dataplane.kill()

    def setup(self):
        self.setUp()

    def teardown(self):
        self.tearDown()
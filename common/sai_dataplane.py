import copy
import os
from unittest import TestCase

import ptf
import ptf.dataplane
from ptf import config

from sai_abstractions import AbstractEntity

# TODO: Get rid of this
# The default configuration dictionary for PTF_NN
config_default = {
    # Miscellaneous options
    "list"               : False,
    "list_test_names"    : False,
    "allow_user"         : False,

    # Switch connection options
    "platform_args"      : None,
    "platform_dir"       : None,
    "interfaces"         : [],
    "device_sockets"     : [],  # when using nanomsg

    # Logging options
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


class SaiDataplane(AbstractEntity, TestCase):

    def __init__(self, exec_params):
        super().__init__(exec_params)
        self.dataplane = None

    def setUp(self):
        assert self.dataplane is not None

    def before_send(self, pkt, device_number=0, port_number=-1):
        pass

    def at_receive(self, pkt, device_number=0, port_number=-1):
        pass

    def tearDown(self):
        assert self.dataplane is not None

    def getPortMap(self):
        """PTF heritage"""
        if config.get('port_map') is None:
            port_map = {}
            for idx, name in self.ifaces.items():
                port_map[(0, int(idx))] = name
        else:
            port_map = config['port_map'].copy()
        return port_map

    def setPortMap(self, port_map):
        """PTF heritage"""
        config["port_map"] = port_map


class SaiHostifDataPlane(SaiDataplane):
    def __init__(self, exec_params, ifaces, dut_ip='localhost'):
        super().__init__(exec_params)
        self.dut_ip = dut_ip
        self.ifaces = ifaces
        self.config = None

    def init(self):
        # Create an instance of PTF dataplane for NN ports
        self.config = copy.deepcopy(config_default)
        # self.config = {}
        self.config.update(copy.deepcopy(config))
        self.config["platform"] = "nn"
        self.dataplane = ptf.dataplane.DataPlane(self.config)
        if "log_dir" not in self.config:
            self.config["log_dir"] = None
        if self.config.get("log_dir") is None:
            if self.config.get("log_file") is None:
                self.config["log_file"] = "ptf_nn.log"
            filename = os.path.splitext(self.config["log_file"])[0] + '.pcap'
            self.dataplane.start_pcap(filename)

        # Add ports to PTF dataplane
        for inum, iname in self.ifaces.items():
            socket_addr = 'tcp://{}:10001'.format(self.dut_ip)
            self.dataplane.port_add(socket_addr, 0, int(inum))

        if 'relax' not in config:
            # Looks like main driver is not PTF and config is empty. So need to add base variables.
            config['relax'] = False

        if ptf.ptfutils.default_timeout is None:
            ptf.ptfutils.default_timeout = 2.0

        self.setUp()

    def deinit(self):
        self.dataplane.stop_pcap()
        self.dataplane.kill()
        self.tearDown()
        self.dataplane = None

    def setUp(self):
        super().setUp()
        self.dataplane.flush()
        if self.config["log_dir"] != None:
            filename = os.path.join(self.config["log_dir"], str(self)) + ".pcap"
            self.dataplane.start_pcap(filename)

    def tearDown(self):
        super().tearDown()
        if self.config["log_dir"] != None:
            self.dataplane.stop_pcap()

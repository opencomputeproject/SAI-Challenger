import ptf
import ptf.dataplane
from ptf import config
import os
import unittest
import copy


class SaiDataPlane(unittest.TestCase):
    def __init__(self, dataplane=None):
        self.dataplane = dataplane

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


class SaiHostifDataPlane(SaiDataPlane):
    def __init__(self, ifaces, dut_ip='localhost'):
        super().__init__()
        self.dut_ip = dut_ip
        self.ifaces = ifaces

    def init(self):
        # Create an instance of PTF dataplane for NN ports
        _config = copy.deepcopy(config)
        _config["platform"] = "nn"
        self.dataplane = ptf.dataplane.DataPlane(_config)
        if _config["log_dir"] == None:
            filename = os.path.splitext(_config["log_file"])[0] + '.pcap'
            self.dataplane.start_pcap(filename)

        # Add ports to PTF dataplane
        for inum, iname in self.ifaces.items():
            socket_addr = 'tcp://{}:10001'.format(self.dut_ip)
            self.dataplane.port_add(socket_addr, 0, int(inum))

        self.setUp()

    def deinit(self):
        self.dataplane.stop_pcap()
        self.dataplane.kill()
        self.tearDown()
        self.dataplane = None
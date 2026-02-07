from sai_dataplane.ptf.sai_ptf_dataplane import SaiPtfDataPlane
from ptf.dataplane import DataPlane
from ptf import config
import copy
import os


class SaiHostifDataPlane(SaiPtfDataPlane):
    def __init__(self, ifaces, dut_ip='localhost'):
        super().__init__()
        self.dut_ip = dut_ip
        self.ifaces = ifaces

    def init(self):
        # Create an instance of PTF dataplane for NN ports
        print(config)
        _config = copy.deepcopy(config)
        _config["platform"] = "nn"
        self.dataplane = DataPlane(_config)
        if _config["log_dir"] is None:
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
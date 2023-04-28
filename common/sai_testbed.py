import imp
import os
import json
import glob
import logging

from saichallenger.common.sai_dut import SaiDut
from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_dpu import SaiDpu
from saichallenger.common.sai_phy import SaiPhy
from saichallenger.common.sai_dataplane.sai_dataplane import SaiDataPlane


class SaiTestbedMeta():

    def __init__(self, base_dir, name):
        try:
            testbed_file = name if name.endswith(".json") else f"{base_dir}/testbeds/{name}.json"
            f = open(testbed_file)
            self.config = json.load(f)
            f.close()
        except Exception as e:
            assert False, f"{e}"

    def get_asic_config(self, alias, asic_type="npu"):
        for cfg in self.config.get(asic_type):
            if cfg.get("alias") == alias:
                return cfg
        return None

    @staticmethod
    def get_asic_dir(base_dir, asic, asic_type="npu"):
        try:
            asic_dir = glob.glob(f"{base_dir}/{asic_type}/**/{asic}", recursive=True)
        except Exception as e:
            assert False, f"{e}"
        return asic_dir[0]

    def get_sku_config(self, base_dir, alias, asic_type="npu"):
        cfg = self.get_asic_config(alias, asic_type)
        sku = cfg.get("sku", None)
        if type(sku) == str:
            asic_dir = self.get_asic_dir(base_dir, cfg["asic"], asic_type)
            try:
                target = cfg.get("target")
                f = open(f"{asic_dir}/{target}/sku/{sku}.json")
                sku = json.load(f)
                f.close()
            except Exception as e:
                assert False, f"{e}"
        return sku


class SaiTestbed():
    def __init__(self, base_dir, name, with_traffic, skip_dataplane=False):
        self.meta = SaiTestbedMeta(base_dir, name)
        self.dut = []
        self.npu = []
        self.dpu = []
        self.phy = []
        self.dataplane = []
        self.name = name
        self.base_dir = base_dir
        self.with_traffic = with_traffic
        self.skip_dataplane = skip_dataplane

    @staticmethod
    def spawn_asic(base_dir, cfg, asic_type="npu"):
        params = cfg.copy()

        asic_dir = SaiTestbedMeta.get_asic_dir(base_dir, params["asic"], asic_type)
        params["asic_dir"] = asic_dir

        asic_mod = None
        module_name = f"sai_{asic_type}"
        try:
            asic_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir]))
        except:
            logging.info("No {} specific module defined..".format(params["asic"]))
            try:
                asic_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir + "/../"]))
            except:
                logging.warn("No NPU specific module defined.")

        asic = None
        if asic_mod is not None:
            try:
                if asic_type == "npu":
                    asic = asic_mod.SaiNpuImpl(params)
                elif asic_type == "dpu":
                    asic = asic_mod.SaiDpuImpl(params)
                elif asic_type == "phy":
                    asic = asic_mod.SaiPhyImpl(params)
                else:
                    assert False, f"Failed to instantiate {asic_type} module"
            except Exception as e:
                assert False, f"{e}"
        else:
            logging.info("Falling back to the default module..")
            if asic_type == "npu":
                asic = SaiNpu(params)
            elif asic_type == "dpu":
                asic = SaiDpu(params)
            elif asic_type == "phy":
                asic = SaiPhy(params)
            else:
                assert False, f"Failed to instantiate default {asic_type} module"
        return asic

    @staticmethod
    def spawn_dataplane(cfg=None):
        return SaiDataPlane.spawn(cfg)

    @staticmethod
    def spawn_dut(cfg=None):
        '''
        SAI testbed may consist of multiple DUTs. Each DUT should be considered
        as a standalone manageable device with its own IP address.
        Each DUT may consist of multiple SAI entities - NPUs, DPUs, extrenal PHYs.
        In a simplest case the DUT has just one SAI entity - NPU or DPU or PHY.
        However, we still should consider DUT management (e.g., prepare DUT
        for TCs runnning) separately of SAI configuration. So, this logic
        has been moved into a separate class `SaiDut`.
        '''
        return SaiDut.spawn(cfg)

    def spawn(self):
        if self.npu or self.dpu or self.phy:
            # to avoid to be executed more than once
            return

        for npu_cfg in self.meta.config.get("npu", []):
            if npu_cfg["client"]["config"].get("mode", None):
                npu_cfg["client"]["config"]["alias"] = npu_cfg["alias"]
                dut = self.spawn_dut(npu_cfg["client"]["config"])
                self.dut.append(dut)
                npu_cfg["dut"] = dut
            npu_cfg["traffic"] = self.with_traffic
            asic = self.spawn_asic(self.base_dir, npu_cfg, "npu")
            self.npu.append(asic)
        for dpu_cfg in self.meta.config.get("dpu", []):
            if dpu_cfg["client"]["config"].get("mode", None):
                dpu_cfg["client"]["config"]["alias"] = dpu_cfg["alias"]
                dut = self.spawn_dut(dpu_cfg["client"]["config"])
                self.dut.append(dut)
                dpu_cfg["dut"] = dut
            dpu_cfg["traffic"] = self.with_traffic
            asic = self.spawn_asic(self.base_dir, dpu_cfg, "dpu")
            self.dpu.append(asic)
        for phy_cfg in self.meta.config.get("phy", []):
            if phy_cfg["client"]["config"].get("mode", None):
                phy_cfg["client"]["config"]["alias"] = phy_cfg["alias"]
                dut = self.spawn_dut(phy_cfg["client"]["config"])
                self.dut.append(dut)
                phy_cfg["dut"] = dut
            phy_cfg["traffic"] = self.with_traffic
            asic = self.spawn_asic(self.base_dir, phy_cfg, "phy")
            self.phy.append(asic)
        for dataplane_cfg in self.meta.config.get("dataplane"):
            dataplane_cfg["traffic"] = self.with_traffic
            dp = self.spawn_dataplane(dataplane_cfg)
            self.dataplane.append(dp)

    def init(self):
        """
        per session init
        """
        self.spawn()

        for dut in self.dut:
            dut.init()

        for npu in self.npu:
            npu.reset()
        for dpu in self.dpu:
            dpu.reset()
        for phy in self.phy:
            phy.reset()
        if not self.skip_dataplane:
            for dp in self.dataplane:
                dp.init()

    def deinit(self):
        """
        per session deinit
        """
        if not self.skip_dataplane:
            for dp in self.dataplane:
                dp.deinit()

    def setup(self):
        """
        per testcase setup
        """
        for dp in self.dataplane:
            dp.setup()

    def teardown(self):
        """
        per testcase teardown
        """
        for dp in self.dataplane:
            dp.teardown()

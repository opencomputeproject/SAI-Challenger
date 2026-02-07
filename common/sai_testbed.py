import glob
import importlib
import json
import logging
import os
import sys

from saichallenger.common.sai_dut import SaiDut
from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_dpu import SaiDpu
from saichallenger.common.sai_phy import SaiPhy
from saichallenger.common.sai_dataplane.sai_dataplane import SaiDataPlane


class SaiTestbedMeta():
    """
    Metadata container for SAI testbed configuration.

    Loads and manages testbed configuration files including topology, SKU-specific
    settings, and test parameters.
    """

    def __init__(self, base_dir, name):
        self.base_dir = base_dir
        try:
            testbed_file = name if name.endswith(".json") else f"{base_dir}/testbeds/{name}.json"
            with open(testbed_file) as f:
                self.config = json.load(f)
        except Exception as e:
            assert False, f"{e}"

    def generate_sai_ptf_config_files(self, alias=None, asic_type="npu"):
        sku_config = self.get_sku_config(alias, asic_type)
        if not sku_config:
            return
        self.config_db = dict()
        self.config_db["PORT"] = dict()
        port_idx = 0
        for index, port in enumerate(sku_config["port"]):
            port_name = port["name"] if "name" in port else "Ethernet" + str(port_idx)
            port_idx += port["lanes"].count(',') + 1
            port_speed = port["speed"] if "speed" in port else sku_config["speed"]
            port_fec = port["fec"] if "fec" in port else sku_config["fec"]
            port_autoneg = port["autoneg"] if "autoneg" in port else sku_config["autoneg"]
            self.config_db["PORT"][port_name] = dict()
            self.config_db["PORT"][port_name]["lanes"] = port["lanes"]
            self.config_db["PORT"][port_name]["admin_status"] = "up"
            self.config_db["PORT"][port_name]["speed"] = port_speed
            self.config_db["PORT"][port_name]["fec"] = port_fec
            self.config_db["PORT"][port_name]["autoneg"] = port_autoneg
            self.config_db["PORT"][port_name]["alias"] = port_name
            self.config_db["PORT"][port_name]["index"] = index + 1

        # Generate config_db.json
        file_path = f"{self.base_dir}/testbeds/config_db.json"
        with open(file_path, "w") as f:
            json.dump(self.config_db, f, indent=4)

        # Generate port_config.ini
        '''
        # name           lanes                alias      speed       index
        Ethernet0        65,66,67,68          etp1       100000      1
        Ethernet4        69,70,71,72          etp2       100000      2
                                  . . . . .
        '''
        line_format = "{:<16}{:<16}{:<16}{:<12}{}"
        line = line_format.format("# name", "lanes", "alias", "speed", "index")
        file_path = f"{self.base_dir}/testbeds/port_config.ini"
        with open(file_path, "w") as f:
            f.write(line + "\n")
            for index, (k, v) in enumerate(self.config_db["PORT"].items()):
                line = line_format.format(k, v["lanes"], k, v["speed"], index + 1)
                f.write(line + "\n")

    def get_asic_config(self, alias, asic_type="npu"):
        for cfg in self.config.get(asic_type):
            if cfg.get("alias") == alias or alias is None:
                return cfg
        return None

    @staticmethod
    def get_asic_dir(base_dir, asic, asic_type="npu"):
        try:
            asic_dir = glob.glob(f"{base_dir}/{asic_type}/**/{asic}", recursive=True)
        except Exception as e:
            assert False, f"{e}"
        return asic_dir[0]

    def get_sku_config(self, alias, asic_type="npu"):
        cfg = self.get_asic_config(alias, asic_type)
        sku = cfg.get("sku", None)
        if isinstance(sku, str):
            asic_dir = self.get_asic_dir(self.base_dir, cfg["asic"], asic_type)
            try:
                target = cfg.get("target")
                with open(f"{asic_dir}/{target}/sku/{sku}.json") as f:
                    sku = json.load(f)
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
    def import_module(root_path, module_name):
        module_specs = importlib.util.spec_from_file_location(module_name, os.path.join(root_path, f"{module_name}.py"))
        module = importlib.util.module_from_spec(module_specs)
        sys.modules[module_name] = module
        module_specs.loader.exec_module(module)
        return module

    @staticmethod
    def spawn_asic(base_dir, cfg, asic_type="npu"):
        params = cfg.copy()

        asic_dir = SaiTestbedMeta.get_asic_dir(base_dir, params["asic"], asic_type)
        params["asic_dir"] = asic_dir

        asic_mod = None
        module_name = f"sai_{asic_type}"
        try:
            asic_mod = SaiTestbed.import_module(asic_dir, module_name)
        except:
            logging.info("No {} specific module defined..".format(params["asic"]))
            try:
                asic_mod = SaiTestbed.import_module(asic_dir + "/../", module_name)
            except:
                logging.warning("No NPU specific module defined.")

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
        for dataplane_cfg in self.meta.config.get("dataplane") or []:
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

        for dut in self.dut:
            dut.deinit()

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

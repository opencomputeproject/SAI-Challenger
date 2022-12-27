import imp
import os
import json
import glob
import logging

from saichallenger.common.sai_npu import SaiNpu
from saichallenger.common.sai_dpu import SaiDpu
from saichallenger.common.sai_dataplane.sai_dataplane import SaiDataPlane


class SaiTestbedMeta():

    def __init__(self, base_dir, name):
        try:
            testbed_file = name if name.endswith(".json") else f"{base_dir}/testbeds/{self.name}.json"
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
        print(f"{base_dir}/{asic_type}/**/{asic}")
        print(asic_dir)
        return asic_dir[0]

    def get_sku_config(self, base_dir, alias, asic_type="npu"):
        cfg = self.get_asic_config(alias, asic_type)
        sku = cfg.get("sku", None)
        if type(sku) == str:
            asic_dir = self.get_asic_dir(base_dir, cfg["asic"], asic_type)
            print(asic_dir)
            try:
                target = cfg.get("target")
                f = open(f"{asic_dir}/{target}/sku/{sku}.json")
                sku = json.load(f)
                f.close()
            except Exception as e:
                assert False, f"{e}"
        return sku


class SaiTestbed():
    def __init__(self, base_dir, name, with_traffic):
        self.meta = SaiTestbedMeta(base_dir, name)
        self.npu = []
        self.dpu = []
        self.dataplane = []
        self.base_dir = base_dir
        self.with_traffic = with_traffic

    @staticmethod
    def spawn_asic(base_dir, cfg, asic_type="npu"):
        params = cfg.copy()
        print(params)

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
            else:
                assert False, f"Failed to instantiate default {asic_type} module"

        if asic is not None:
            asic.reset()
        return asic

    @staticmethod
    def spawn_dataplane(cfg=None):
        return SaiDataPlane.spawn(cfg)

    def init(self):
        """
        per session init
        """
        for npu_cfg in self.meta.config.get("npu", []):
            npu_cfg["traffic"] = self.with_traffic
            self.npu.append(self.spawn_asic(self.base_dir, npu_cfg, "npu"))
        for dpu_cfg in self.meta.config.get("dpu", []):
            dpu_cfg["traffic"] = self.with_traffic
            self.dpu.append(self.spawn_asic(self.base_dir, dpu_cfg, "dpu"))
        for dataplane_cfg in self.meta.config.get("dataplane"):
            dp = self.spawn_dataplane(dataplane_cfg)
            if dp is not None:
                dp.init()
                self.dataplane.append(dp)

    def deinit(self):
        """
        per session deinit
        """
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

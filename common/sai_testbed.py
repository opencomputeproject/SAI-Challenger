import imp
import os
import json
import glob
import logging

from sai_npu import SaiNpu
from sai_dataplane import SaiPtfDataPlane

cur_dir = os.path.dirname(os.path.abspath(__file__))       

class SaiTestbedMeta():

    def __init__(self, name):
        self.name = name
        try:
            f = open(f"{cur_dir}/../testbeds/{self.name}.json")
            self.config = json.load(f)
            f.close()
        except Exception as e:
            assert False, f"{e}"

    def get_duts(self):
        return self.config["duts"]

    def get_dataplanes(self):
        return self.config.get("dataplanes", None)

    def get_dut_config(self, dut):
        return self.config[dut]

    def get_dataplane_config(self, dataplane):
        return self.config[dataplane]

    @staticmethod
    def get_asic_dir(asic):
        try:
            asic_dir = glob.glob(cur_dir + "/../npu/**/" + asic, recursive=True)
        except Exception as e:
            assert False, f"{e}"
        return asic_dir[0]

    def get_sku_config(self, dut):
        dut_cfg = self.get_dut_config(dut)
        sku = dut_cfg.get("sku", None)
        if type(sku) == str:
            asic_dir = self.get_asic_dir(dut_cfg["asic"])
            print(asic_dir)
            try:
                target = dut_cfg["target"]
                f = open("{}/{}/sku/{}.json".format(asic_dir, target, sku))
                sku = json.load(f)
                f.close()
            except Exception as e:
                assert False, f"{e}"
        return sku

class SaiTestbed():
    def __init__(self, name):
        self.meta = SaiTestbedMeta(name)
        self.dut = []
        self.dataplane = []

    @staticmethod
    def spawn_npu(cfg):

        params = {
            "mgmt_ip": cfg.get("mgmt_ip", "localhost"),
            "traffic": cfg.get("traffic", False),
            "saivs": cfg.get("saivs", False),
            "loglevel": cfg.get("loglevel", "NOTICE"),
            "sku": cfg.get("sku", None),
            "asic": cfg["asic"],
            "asic_dir": None,
            "target": cfg["target"]
        }
        print(params)

        asic_dir = SaiTestbedMeta.get_asic_dir(cfg["asic"])
        params["asic_dir"] = asic_dir

        npu_mod = None
        module_name = "sai_npu"
        try:
            npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir]))
        except:
            logging.info("No {} specific 'sai_npu' module defined..".format(params["asic"]))
            try:
                npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir + "/../"]))
            except:
                logging.warn("No NPU specific 'sai_npu' module defined.")

        npu = None
        if npu_mod is not None:
            try:
                npu = npu_mod.SaiNpuImpl(params)
            except Exception as e:
                assert False, f"{e}"
        else:
            logging.info("Falling back to the default 'sai_npu' module..")
            npu = SaiNpu(params)

        if npu is not None:
            npu.reset()
        return npu

    @staticmethod
    def spawn_dataplane(cfg):
        return SaiPtfDataPlane(cfg)

    def init(self):
        """
        per session init
        """
        for dut in self.meta.get_duts():
            cfg = self.meta.get_dut_config(dut)
            self.dut.append(self.spawn_npu(cfg))
        for dataplane in self.meta.get_dataplanes():
            cfg = self.meta.get_dataplane_config(dataplane)
            dp = self.spawn_dataplane(cfg)
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

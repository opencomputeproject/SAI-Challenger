import sys
import pytest
from saichallenger.common.sai_testbed import SaiTestbedMeta


def import_base_modules():
    sys.path.insert(0, '/sai-challenger/ptf/src')

import_base_modules()


@pytest.fixture(scope="session", autouse=True)
def set_ptf_params(request):
    if request.config.option.testbed:
        tb_params = SaiTestbedMeta("/sai-challenger", request.config.option.testbed)
        ports = to_ptf_int_list(tb_params.config['dataplane'][0]['port_groups'])
    else:
        ports = ""
    
    arg_back = sys.argv
    # provide required PTF runner params to avoid exiting with an error
    sys.argv = ['ptf.py','--test-dir', '/sai-challenger/sai/ptf', *ports]

    # load PTF runner module to let it collect test params into ptf.config
    import imp
    ptf_runner = imp.load_source('runner', '/sai-challenger/ptf/ptf')
    print("PTF params: ", ptf_runner.config)

    sys.argv = arg_back

    import ptf
    # Set up the dataplane
    ptf.dataplane_instance = ptf.dataplane.DataPlane(ptf_runner.config)
    ptf_runner.pcap_setup(ptf_runner.config)
    for port_id, ifname in ptf_runner.config["port_map"].items():
        device, port = port_id
        ptf.dataplane_instance.port_add(ifname, device, port)

    yield

    ptf.dataplane_instance.stop_pcap()
    ptf.dataplane_instance.kill()
    ptf.dataplane_instance = None


def pytest_addoption(parser):
    parser.addoption("--testbed", action="store", default=None, help="Testbed name")

    
def to_ptf_int_list(port_map):
    ports = [f"{m['alias']}@{m['name']}" for m in port_map]
    return " ".join([f"--interface {port}" for port in ports]).split(" ")

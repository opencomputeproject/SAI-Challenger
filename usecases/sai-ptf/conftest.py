import sys
import pytest
import subprocess
from saichallenger.common.sai_testbed import SaiTestbedMeta

sys.path.insert(0, '/sai-challenger/ptf/src')


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    patch_file = "/sai-challenger/usecases/sai-ptf/patches/0001-sai-base-test.patch"
    target_directory = "/sai-challenger/usecases/sai-ptf/SAI/"

    try:
        command = ["patch", "--dry-run", "--silent", "-N", "-p1", "-i", patch_file, "-d", target_directory]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            subprocess.run(["patch", "-p1", "-i", patch_file, "-d", target_directory], check=True)
        elif result.returncode == 1:
            # The patch is already applied
            return
        else:
            raise RuntimeError(f"Failed to check whether the patch is already applied: {result}")
    except Exception as e:
        raise RuntimeError(f"Failed to apply the patch: {e}")


@pytest.fixture(scope="session", autouse=True)
def set_ptf_params(request):
    if request.config.option.testbed:
        tb_params = SaiTestbedMeta("/sai-challenger", request.config.option.testbed)
        if tb_params.config['npu'][0]['target'] == 'saivs' and \
           tb_params.config['npu'][0]['client']['config']['ip'] in ['localhost', '127.0.0.1']:
            try:
                # Clean-up saiserver after previous test session
                subprocess.run(["supervisorctl", "restart", "saiserver"], check=True)
            except Exception as e:
                raise RuntimeError(f"Failed to restart the saiserver: {e}")

        tb_params.generate_sai_ptf_config_files()
        ports = to_ptf_int_list(tb_params.config['dataplane'][0]['port_groups'])
    else:
        ports = ""
    
    arg_back = sys.argv
    # provide required PTF runner params to avoid exiting with an error
    sys.argv = ['ptf.py','--test-dir', '/sai-challenger/usecases/sai-ptf/SAI/ptf', *ports]
    sys.argv.append("--test-params")
    sys.argv.append(f"thrift_server='{tb_params.config['npu'][0]['client']['config']['ip']}';config_db_json='/sai-challenger/testbeds/config_db.json'")

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

import glob
import json
import logging
import os
import sys
import imp

# Setup JSON root keys
CONNECTIONS = 'CONNECTIONS'
SUPPORTED_SETUP_KEYS = ('DATAPLANE', 'NPU', 'DPU', CONNECTIONS)


def init_setup(options):

    config_file_path = options.option.setup

    # Load provided config
    with open(config_file_path) as config_fh:
        config_data = json.load(config_fh)

    # TODO: Load defaults data

    return load_implementations(config_data, options=options) if config_data else dict()


def form_equip_connections(global_connections, equip):
    """Create links attribute in device config using CONNECTIONS section of JSON setup."""

    equip['links'] = {}
    for link_direction, links in global_connections.items():
        if equip['alias'] not in link_direction:
            continue
        src_dev, dst_dev = link_direction.split('->')
        if equip['alias'] == src_dev:
            equip['links'][dst_dev] = [link[:] for link in links]
        else:
            equip['links'][src_dev] = [list(reversed(link)) for link in links]


def load_npu_module(equip_type, equip):
    """Load NPU implementation module.
    Expected folder structure is described in docs/porting_guide.md
    """

    equip["asic_dir"] = None
    asic_name = equip.get("asic")
    asic_dir = None
    npu_mod = None
    module_name = f"sai_{equip_type.lower()}"

    if asic_name:
        try:
            asic_dir = glob.glob(f"../{equip_type.lower()}/**/{asic_name}/", recursive=True)
            asic_dir = asic_dir[0]
            equip["asic_dir"] = asic_dir
        except:
            logging.critical(f"Failed to find {asic_name} in {equip_type} folder")
            sys.exit(1)

    try:
        npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir]))
    except:
        logging.info(f"No specific '{module_name}' module defined in {asic_dir}.")
        logging.info(f"Looking for '{module_name}' in {os.path.abspath(asic_dir + '../')}.")
        try:
            npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir + "../"]))
        except:
            logging.warn(f"No {equip_type} specific module {module_name} defined.")

    return module_name, npu_mod

def load_dpu_module(equip_type, equip):
    """Load DPU implementation module.
    Expected folder structure is described in docs/porting_guide.md
    """

    equip["asic_dir"] = None
    asic_name = equip.get("asic")
    asic_dir = None
    dpu_mod = None
    module_name = f"sai_{equip_type.lower()}"

    if asic_name:
        try:
            asic_dir = glob.glob(f"../{equip_type.lower()}/**/{asic_name}/", recursive=True)
            asic_dir = asic_dir[0]
            equip["asic_dir"] = asic_dir
        except:
            logging.critical(f"Failed to find {asic_name} in {equip_type} folder")
            sys.exit(1)

    try:
        dpu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir]))
    except:
        logging.info(f"No specific '{module_name}' module defined in {asic_dir}.")
        logging.info(f"Looking for '{module_name}' in {os.path.abspath(asic_dir + '../')}.")
        try:
            dpu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir + "../"]))
        except:
            logging.warn(f"No {equip_type} specific module {module_name} defined.")

    return module_name, dpu_mod

def load_dataplane_module(equip_type, equip):
    """Load DATAPLANE implementation module.
    Expeted folder structure is described in docs/TODO.md
    """

    dataplane_name = equip.get("type")
    dataplane_mod = None
    module_name = f"sai_{equip_type.lower()}"

    try:
        impl_dir = glob.glob(f"../{equip_type.lower()}/{dataplane_name}/", recursive=True)
        impl_dir = impl_dir[0]
        equip["impl_dir"] = impl_dir
    except:
        logging.critical(f"Failed to find {dataplane_name} in {equip_type} folder.")
        sys.exit(1)

    try:
        dataplane_mod = imp.load_module(module_name, *imp.find_module(module_name, [impl_dir]))
    except:
        logging.warn(f"No {equip_type} specific module {module_name} defined in {impl_dir} folder.")

    return module_name, dataplane_mod


def load_implementations(setup_dict, options=None):
    """Load required module.class implementations for a specific item in the JSON setup config."""

    instances_dict = dict()
    devices = dict()

    for equip_type in setup_dict:

        if equip_type not in SUPPORTED_SETUP_KEYS:
            raise ValueError(f"Unsupported root key {equip_type} in setup file. Supported: {SUPPORTED_SETUP_KEYS}")
        elif equip_type == CONNECTIONS:
            continue

        instances_dict[equip_type] = list()
        for equip in setup_dict[equip_type]:

            equip['loglevel'] = options.option.loglevel
            # TODO: remove run_traffic from Sai NPU.
            equip['traffic'] = options.option.traffic
            # NOTE: form_equip_connections() will modify dev dict inside
            if CONNECTIONS in setup_dict and setup_dict[CONNECTIONS]:
                form_equip_connections(setup_dict[CONNECTIONS], equip)

            module_name, impl_mod = globals()[f"load_{equip_type.lower()}_module"](equip_type, equip)

            if impl_mod is not None:
                try:
                    class_name = f"Sai{equip_type.capitalize()}Impl"
                    instance = getattr(impl_mod, class_name)(equip)
                except:
                    logging.critical(f"Failed to instantiate '{module_name}.{class_name}' module for {equip_type}:{equip['alias']}.")
                    sys.exit(1)
            else:
                class_name = f"Sai{equip_type.capitalize()}"
                logging.info(f"{module_name} module is not found in '{equip_type.lower()}' folder." +
                             f"Falling back to the default '{module_name}.{class_name}' module.")
                impl_mod = __import__(module_name)
                instance = getattr(impl_mod, class_name)(equip)

            instance.init_port_groups()
            devices[instance.alias] = instance
            instances_dict[equip_type].append(instance)

    # Add neighbors attribute
    for equip_type in instances_dict.keys():
        for item in instances_dict[equip_type]:
            item.neighbors = devices
            item.init_connections()

    return instances_dict

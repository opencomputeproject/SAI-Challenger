from itertools import chain

# Constans:
MIXED = "mixed"  # mixed speed mode


def connections_processing_lock(method):
    """Lock connections updates to prevent loops in init_connections call."""

    def wrap(self):
        self.connections_processing_lock = True
        try:
            return method(self)
        finally:
            self.connections_processing_lock = False

    return wrap


class Port:
    """
    Device port representation

    Parameters:
        device (str): Device name
        id (int): Internal port ID used in test cases
        alias (str): Real port ID on device
        speed (str): Port speed
    """

    def __init__(self, device=None, id=None, alias=None, speed=None):
        self.device = device
        self.id = id
        self.alias = alias
        self.speed = speed
        self.neighbor = None

    def __str__(self):
        return '%s[id:%s]' % (self.port, self.id)


class AbstractEntity:

    def __init__(self, exec_params):
        # Setup info
        self.exec_params = exec_params
        # Device info
        self.driver = exec_params['type']

        # Port group attributes
        self.global_port_group_mode = None
        self.port_instances = None
        self.ports = None  # Basic list od dport aliases
        self.speeds = None  # Basic list od port speeds
        # Lock to avoid recursion during port_grops processing
        self.connections_processing_lock = False
        # Connected devices
        self.neighbors = None

    @connections_processing_lock
    def init_connections(self):
        """
        Create connections description. Assign dictionary of links to the device containing:
            link ID, port name, device name and same params for the remote device link.

        dev_dict['NPU'][0].linked_ports
        {'vs': [<Port object at 0x0...>,
                <Port object at 0x1...>]}
        """

        linked_ports = dict()

        for linked_device in self.exec_params["links"]:

            linked_ports[linked_device] = list()
            neighbor = self.neighbors[linked_device]

            if isinstance(self.exec_params["links"][linked_device], list):

                own_name_id_map = {}
                neigh_name_id_map = {}
                for indx, port in enumerate(self.exec_params['port_groups']):
                    own_name_id_map[port['alias']] = indx
                for indx, port in enumerate(neighbor.exec_params['port_groups']):
                    neigh_name_id_map[port['alias']] = indx

                for own_pg_name, neigh_pg_name in self.exec_params["links"][linked_device]:

                    own_pg_id = own_name_id_map[own_pg_name]
                    neigh_pg_id = neigh_name_id_map[neigh_pg_name]
                    own_mode = self.exec_params['port_groups'][own_pg_id]['current']
                    neigh_mode = neighbor.exec_params['port_groups'][neigh_pg_id]['current']
                    own_pg = self.exec_params['port_groups'][own_pg_id][own_mode]
                    neigh_pg = neighbor.exec_params['port_groups'][neigh_pg_id][neigh_mode]

                    if not isinstance(own_pg, list):
                        own_pg = [own_pg]
                    if not isinstance(neigh_pg, list):
                        neigh_pg = [neigh_pg]

                    # zip() skips unpaired ports. So if number of ports in group is different only first ones will
                    # be connected to each other.
                    for o_port, n_port in zip(own_pg, neigh_pg):
                        o_iport = self.port_instances[self.ports.index(o_port)]
                        o_iport.neighbor = neighbor.port_instances[neighbor.ports.index(n_port)]
                        linked_ports[linked_device].append(o_iport)

            elif isinstance(self.exec_params["links"][linked_device], dict):
                # Basic setup processing
                for own_port, neighbor_port in self.exec_params["links"][linked_device].items():
                    _port = self.port_instances[self.ports.index(own_port)]
                    _port.neighbor = neighbor.port_instances[neighbor.ports.index(neighbor_port)]
                    linked_ports[linked_device].append(_port)
            else:
                raise ValueError('exec_params links attribute has to be dict or list only.')

        self.linked_ports = linked_ports

        # Update links for neighbor devices.
        for neighbor in chain(self.neighbors.values()):
            if self is neighbor:
                # Skip self
                continue
            if neighbor.connections_processing_lock or neighbor.neighbors is None:
                # Skip already processing and not even inited devices.
                continue
            neighbor.init_connections()

    def init_port_groups(self, mode=None):
        """
        Generate 'ports' and 'speeds' attributes based on exec_params.

        Parmeters:
            mode (str or list(str)): Examples - "10G" or list ["10G", "10G", "25G"]
        """

        # Get ports config
        port_groups = self.exec_params.get('port_groups')
        self.global_port_group_mode = mode or self.global_port_group_mode

        if self.global_port_group_mode is None:
            # Most probably it is the 1st init
            modes = set([p['init'] for p in self.exec_params["port_groups"]])
            if len(modes) == 1:
                self.global_port_group_mode = modes.pop()
            else:
                self.global_port_group_modes = MIXED

        # Plain ports' names and speeds lists
        simple_ports = []
        simple_speeds = []

        if isinstance(mode, list):
            # User are about to switch mode
            assert len(mode) == len(port_groups), 'Custom modes does not correspond to port group count.'
            # self.global_port_group_mode has to be string
            self.global_port_group_mode = MIXED

        # Parse each port dict
        for pid, port_group in enumerate(port_groups):
            # Get mode: 1) user set value, 2) current value; 3) init value
            if isinstance(mode, list):
                # each port's mode is set explicitly
                port_mode = mode[pid]
            elif mode is None or mode == MIXED:
                # port's mode is not set. use init or current value
                port_mode = port_group.get('current', port_group.get('init'))
            else:
                # the single port's mode value is set for all port groups
                port_mode = mode
            assert port_mode is not None, f"Init mode doesn't set for port '{port_group}'."
            port_name = port_group.get(port_mode)
            assert port_name is not None, f"Mode '{port_mode}' isn't defined for port '{port_group}'"
            # Store 'current mode'
            port_group['current'] = port_mode
            # Set speeds
            if not isinstance(port_name, list):
                port_name = [port_name]
            # Same speed for all ports
            modes = [port_mode for _ in port_name]
            simple_ports += port_name
            simple_speeds += modes

        # Build port_instances list
        self.port_instances = []
        for indx, (port_group, speed) in enumerate(zip(simple_ports, simple_speeds)):
            self.port_instances.append(Port(self, indx, port_group, speed))

        self.ports = simple_ports
        self.speeds = simple_speeds

import logging
import sys

import dpkt
import saichallenger.common.sai_dataplane.utils.traffic_utils as tt
from scapy.layers.l2 import Ether

import ptf.testutils as ptfTestutils

default_step = 0.2
default_timeout = 2
default_n_timeout = 2


class SnappiDataPlaneUtilsWrapper:

    _instances = {}

    def __init__(self, dataplane):
        self._dataplane = dataplane
        self._flow_name_counter = 0

    def __getattr__(self, v):
        if v not in self.__dict__:
            try:
                return getattr(self._dataplane, v)
            except AttributeError:
                raise AttributeError(f"Not {self.__class__.__name__} not {self._dataplane.__class__.__name__} does notcontain {v}.")

    def __new__(cls, dataplane):
        id_d = id(dataplane)
        if id_d in cls._instances:
            return cls._instances[id_d]
        else:
            cls._instances[id_d] = object.__new__(cls)
            return cls._instances[id_d]

    def add_tcp_flow(self, packet, port_id, packets_count=1, flow_name=None):

        port_cfg = self.configuration.ports.serialize('dict')[port_id]

        flow_name = flow_name or self.create_default_flow_name(port_id, id(packet))

        flow = self.configuration.flows.flow(name=flow_name)[-1]
        flow.tx_rx.port.tx_name = port_cfg['name']

        flow.size.fixed = len(packet)
        flow.duration.fixed_packets.packets = packets_count

        flow.packet.ethernet().ipv4().tcp().custom()

        eth = flow.packet[0]
        eth.src.value = packet[0].fields['src']
        eth.dst.value = packet[0].fields['dst']

        ipv4 = flow.packet[1]
        ipv4.dst.value = packet[1].fields['dst']
        ipv4.src.value = packet[1].fields['src']
        ipv4.time_to_live.value = packet[1].fields['ttl']
        ipv4.identification.value = packet[1].fields['id']

        tcp = flow.packet[2]
        tcp.dst_port.value = packet[2].fields['dport']
        tcp.src_port.value = packet[2].fields['sport']
        tcp.window.value = packet[2].window
        pos = 2
        tcp.ctl_syn.value = (packet[2].fields['flags'].value & pos) >> (pos - 1)

        payload = flow.packet[3]
        payload.bytes = packet[2].payload.build().hex()

        self.set_config()

    def create_default_flow_name(self, port_id, packet_id):
        self._flow_name_counter += 1
        return "flow_{}_{}_{}".format(port_id, packet_id, self._flow_name_counter)

    def add_raw_flow(self, packet, port_id, packets_count=1, flow_name=None):

        port_cfg = self.configuration.ports.serialize('dict')[port_id]

        flow_name = flow_name or self.create_default_flow_name(port_id, id(packet))

        flow = self.configuration.flows.flow(name=flow_name)[-1]
        flow.tx_rx.port.tx_name = port_cfg['name']

        flow.size.fixed = len(packet)
        flow.duration.fixed_packets.packets = packets_count

        flow.packet.ethernet().custom()

        eth = flow.packet[0]
        eth.src.value = packet[0].fields['src']
        eth.dst.value = packet[0].fields['dst']
        eth.ether_type.value = packet[0].type
        # eth.pfc_queue.value = 3

        payload = flow.packet[1]
        payload.bytes = packet[0].payload.build().hex()

        self.set_config()

    def send_packet(self, port_id, pkt, count=1):
        """ptf.testutils.send_packet"""
        self.add_raw_flow(pkt, port_id, packets_count=count)
        self.start_traffic()

    def get_capture_function_and_request(self, port_name):
        capture_request = self.api.capture_request()
        capture_request.port_name = port_name
        capture_function = self.api.get_capture
        return capture_function, capture_request

    def get_pcap_bytes_by_polling(self, port_name, timeout, step):
        logging.info(f'Fetching capture from port {port_name}')
        capture_func, capture_req = self.get_capture_function_and_request(port_name)
        pcap_bytes = tt.pcap_bts_polling(self.api.get_capture, capture_req, timeout, step)
        # Restart capture.
        # Default PTF behavior is to have running capture during the test case.
        self.start_capture()
        return pcap_bytes

    def verify_captures_on_port(self, exp_pkts, port_id):
        """ Returns true if all packets captured on specified port matches list of exp_packets
        Throws assertion if not true
        exp_pkts - list of expected packets
        cap_port_name - single port to examine
        """
        port_cfg = self.configuration.ports.serialize('dict')[port_id]
        port_name = port_cfg['name']
        cap_dict = {}
        logging.info(f'Fetching capture from port {port_name}')
        capture_func, capture_req = self.get_capture_function_and_request(port_name)
        pcap_bytes = capture_func(capture_req)
        self.start_capture()

        cap_dict[port_name] = []
        for ts, pkt in dpkt.pcap.Reader(pcap_bytes):
            if sys.version_info[0] == 2:
                raw = [ord(b) for b in pkt]
            else:
                raw = list(pkt)
            cap_dict[port_name].append(raw)

        cap_pkts = cap_dict[port_name]
        assert len(exp_pkts) == len(cap_pkts), f"Expected {len(exp_pkts)} packets, captured {len(cap_pkts)}"

        logging.info(f"Comparing {len(exp_pkts)} expected packets to {len(cap_pkts)} captured packets")

        i = 0
        for pkt in cap_pkts:
            brx = bytes(cap_pkts[i])
            rx_pkt = Ether(brx)

            # print("[%d] %s =? %s" % (i, exp_pkts[i], rx_pkt))
            (equal, reason, p1, p2) = tt.compare_pkts2(exp_pkts[i], rx_pkt)

            if not equal:
                logging.info("Mismatched pkt #%d: %s" % (i, reason))
                logging.info("\nExpected (masked):\n===============")
                p1.show()
                logging.info("\nReceived (masked):\n===============")
                p2.show()

                tt.print_pkts_side_by_side(p1, p2)

                assert equal, f"Packets don't match: {str(p1)} != {str(p2)}"
            i += 1
        return True

    def verify_no_any_packet(self, port_id, timeout=None, step=None):
        """ Returns true if no bytes captured on a port
        cap_port_names - list of ports to examine
        returns True if condition passes, else asserts
        """
        port_cfg = self.configuration.ports.serialize('dict')[port_id]
        port_name = port_cfg['name']

        pcap_bytes = self.get_pcap_bytes_by_polling(port_name, timeout, step)

        logging.info(f'Verifying empty capture from port {port_name}')
        assert not any(pcap_bytes), f"A packet was received on device 0, port {port_id}:{port_name}, but we expected no packets."
        return True

    def verify_packet(self, pkt, port_id, timeout=None, step=None):
        """ Returns true if all packets captured on specified port match exp_packet
        pkt - expected packet
        port_id - single port to examine
        timeout - time to poll exp_pkt
        step - time before the next poll
        """
        port_cfg = self.configuration.ports.serialize('dict')[port_id]
        port_name = port_cfg['name']
        cap_dict = {}

        pcap_bytes = self.get_pcap_bytes_by_polling(port_name, timeout, step)

        cap_dict[port_name] = []
        try:
            for ts, pcap_pkt in dpkt.pcap.Reader(pcap_bytes):
                if sys.version_info[0] == 2:
                    raw = [ord(b) for b in pcap_pkt]
                else:
                    raw = list(pcap_pkt)
                cap_dict[port_name].append(raw)
        except Exception as err:
            # Handle only error when buffer is empty.
            if "got 0, 24 needed at least" not in str(err):
                logging.warning(f"Error on capture buffer read: {err}")
                raise

        cap_pkts = cap_dict[port_name]

        for cap_pkt in cap_pkts:
            indx_to_cut = len(cap_pkt) - 4
            cap_pkt = cap_pkt[:indx_to_cut]  # delete FCS
            assert len(pkt) == len(cap_pkt), f"Expected {len(pkt)}B packets, captured {len(cap_pkt)}B"

            brx = bytes(cap_pkt)
            rx_pkt = Ether(brx)

            (equal, reason, p1, p2) = tt.compare_pkts2(pkt, rx_pkt)

            if not equal:
                logging.info(f'Not expected packet received on port {port_name} id {port_id}')
                logging.info("\nNot expected (masked):\n===============")
                p1.show()

                logging.info("\nReceived (masked):\n===============")
                p2.show()

                tt.print_pkts_side_by_side(p1, p2)

                assert equal, f"Packets don't match: {str(p1)} != {str(p2)}"
        else:
            assert cap_pkts, "No packets captured"

        return True

    def verify_packets(self, packet, ports_id, device_number=0, timeout=None, n_timeout=None, step=None):
        """
        Check that a packet is received on each of the specified port numbers

        Also verifies that the packet is not received on any other ports
        and that no other packets are received

        packet - packet to examine
        ports_id - ports to examine
        timeout - timeout in which we are expecting pkt to arrive in
        n_timeout - timeout for which we will wait for to check for unexpected pkts
        step - time before the next poll

        WARNING: device_number is ignored so far
        """
        all_port_ids_names = [(port_id, port.alias) for port_id, port in enumerate(self.configuration.ports)]

        for port_id, port_name in all_port_ids_names:
            if port_id in ports_id:
                self.verify_packet(packet, port_id, timeout, step)
            else:
                self.verify_no_packet(packet, port_id, n_timeout, step)
                self.verify_no_any_packet(port_id, n_timeout, step)

    def verify_no_packet(self, pkt, port_id, timeout=None, step=None):
        """ Returns true if all packets captured on specified port do NOT match not_exp_packet
        pkt - not expected packet
        port_id - single port to examine
        timeout - time to poll not_exp_pkt
        step - time before the next poll
        """
        port_cfg = self.configuration.ports.serialize('dict')[port_id]
        port_name = port_cfg['name']
        cap_dict = {}

        pcap_bytes = self.get_pcap_bytes_by_polling(port_name, timeout, step)

        cap_dict[port_name] = []

        if len(pcap_bytes.getvalue()) == 0:
            return True
        else:
            for ts, pcap_pkt in dpkt.pcap.Reader(pcap_bytes):
                if sys.version_info[0] == 2:
                    raw = [ord(b) for b in pcap_pkt]
                else:
                    raw = list(pcap_pkt)
                cap_dict[port_name].append(raw)

            cap_pkts = cap_dict[port_name]

            for cap_pkt in cap_pkts:
                indx_to_cut = len(cap_pkt) - 4
                cap_pkt = cap_pkt[:indx_to_cut]  # delete FCS
                if len(pkt) != len(cap_pkt):
                    continue

                brx = bytes(cap_pkt)
                rx_pkt = Ether(brx)

                (equal, reason, p1, p2) = tt.compare_pkts2(pkt, rx_pkt)

                if equal:
                    logging.info(f'Not expected packet received on port {port_name} id {port_id}')
                    logging.info("\nNot expected (masked):\n===============")
                    p1.show()

                    logging.info("\nReceived (masked):\n===============")
                    p2.show()

                    tt.print_pkts_side_by_side(p1, p2)

                    assert not equal, f"Packets match: {str(p1)} == {str(p2)}"

            return True

    def verify_no_other_packets(self, device_number=0, timeout=None, step=None):
        """Check that no unexpected packets are received on specified device
        This is a no-op if the --relax option is in effect.

        WARNING: device_number is ignored so far
        """

        for pid, port in enumerate(self.configuration.ports.serialize('dict')):
            # port_name = self.configuration.ports.serialize('dict')[port_id]['name']
            # logging.info(f'Fetching capture from port {port_name}')
            # capture_req = self.api.capture_request()
            # capture_req.port_name = port_name

            # pcap_bytes = pcap_bts_polling(self.api.get_capture, capture_req, timeout, step)

            # assert len(pcap_bytes.getvalue()) == 0, \
            #     "A packet was received on device {}, port {}:{}, but we expected no packets.".format(
            #         device_number, port_id, port_name)
            self.verify_no_any_packet(pid, timeout, step)

        return True

    def verify_any_packet_any_port(self, pkts=[], ports=[], device_number=0, timeout=None, n_timeout=None):
        """
        a.) Check that _any_ of the packet is received on _any_ of the specified ports belonging to
        the given device (default device_number is 0).

        b.) Also verifies that the packet is not received on any other ports for this
        device, and that no other packets are received on the device (unless --relax
        is in effect).

        Returns the index of the port on which the packet is received.
        Timeout for this function is used as +ve timeout for (a) and n_timeout is used for
        -ve timeout for (b)
        Note: +ve timeout here means timeout in which we are expecting pkt to arrive in
        -ve timeout here means timeout for which we will wait for to check for unexpected pkts

        The function may verify both: not masked and masked packets
        """

        cap_dict = {}
        for port_id in self.configuration.ports.serialize('dict'):
            if port_id not in ports:
                continue
            port_name = self.configuration.ports.serialize('dict')[port_id]['name']

            pcap_bytes = self.get_pcap_bytes_by_polling(port_name, timeout, step)

            cap_dict[port_name] = pcap_bytes
            timeout = 0  # Reduce timeout

        found_packet = False

        for port_name, pcap_bytes in cap_dict.items():

            cap_list = []
            for ts, pcap_pkt in dpkt.pcap.Reader(pcap_bytes):
                raw = list(pcap_pkt)
                cap_list.append(raw)

            for cap_pkt in cap_list:
                indx_to_cut = len(cap_pkt) - 4
                cap_pkt = cap_pkt[:indx_to_cut]  # delete FCS

                for exp_pkt in pkts:
                    if len(exp_pkt) != len(cap_pkt):
                        continue
                    brx = bytes(cap_pkt)
                    rx_pkt = Ether(brx)
                    (equal, reason, p1, p2) = tt.compare_pkts2(exp_pkt, rx_pkt)
                    if equal:
                        logging.info(f'Packet received on port {port_name} id {port_id}')
                        logging.info("\nExpected (masked):\n===============")
                        p1.show()
                        logging.info("\nReceived (masked):\n===============")
                        p2.show()
                        tt.print_pkts_side_by_side(p1, p2)
                        found_packet = True
        assert found_packet, "Any of expected packets is not received on any expected port"

        n_timeout = n_timeout or default_n_timeout
        self.verify_no_other_packets(device_number=device_number, timeout=n_timeout)


def dataplane_redirect(function):
    def wrapper(*a, **kw):
        if a[0].driver != 'snappi':
            return getattr(ptfTestutils, function.__name__)(*a, **kw)
        else:
            wrapperObject = SnappiDataPlaneUtilsWrapper(a[0])
            return getattr(wrapperObject, function.__name__)(*a[1:], **kw)
            # return function(*a, **kw)
    return wrapper


def simple_arp_packet(*a, **kw):
    return ptfTestutils.simple_arp_packet(*a, **kw)


def simple_eth_packet(*a, **kw):
    return ptfTestutils.simple_eth_packet(*a, **kw)


def simple_geneve_packet(*a, **kw):
    return ptfTestutils.simple_geneve_packet(*a, **kw)


def simple_gre_erspan_packet(*a, **kw):
    return ptfTestutils.simple_gre_erspan_packet(*a, **kw)


def simple_gre_packet(*a, **kw):
    return ptfTestutils.simple_gre_packet(*a, **kw)


def simple_grev6_packet(*a, **kw):
    return ptfTestutils.simple_grev6_packet(*a, **kw)


def simple_icmp_packet(*a, **kw):
    return ptfTestutils.simple_icmp_packet(*a, **kw)


def simple_icmpv6_packet(*a, **kw):
    return ptfTestutils.simple_icmpv6_packet(*a, **kw)


def simple_igmp_packet(*a, **kw):
    return ptfTestutils.simple_igmp_packet(*a, **kw)


def simple_ip_only_packet(*a, **kw):
    return ptfTestutils.simple_ip_only_packet(*a, **kw)


def simple_ip_packet(*a, **kw):
    return ptfTestutils.simple_ip_packet(*a, **kw)


def simple_ipv4ip_packet(*a, **kw):
    return ptfTestutils.simple_ipv4ip_packet(*a, **kw)


def simple_ipv6_mld_packet(*a, **kw):
    return ptfTestutils.simple_ipv6_mld_packet(*a, **kw)


def simple_ipv6_sr_packet(*a, **kw):
    return ptfTestutils.simple_ipv6_sr_packet(*a, **kw)


def simple_ipv6ip_packet(*a, **kw):
    return ptfTestutils.simple_ipv6ip_packet(*a, **kw)


def simple_mpls_packet(*a, **kw):
    return ptfTestutils.simple_mpls_packet(*a, **kw)


def simple_nvgre_packet(*a, **kw):
    return ptfTestutils.simple_nvgre_packet(*a, **kw)


def simple_qinq_tcp_packet(*a, **kw):
    return ptfTestutils.simple_qinq_tcp_packet(*a, **kw)


def simple_rocev2_packet(*a, **kw):
    return ptfTestutils.simple_rocev2_packet(*a, **kw)


def simple_rocev2v6_packet(*a, **kw):
    return ptfTestutils.simple_rocev2v6_packet(*a, **kw)


def simple_tcp_packet(*a, **kw):
    return ptfTestutils.simple_tcp_packet(*a, **kw)


def simple_tcpv6_packet(*a, **kw):
    return ptfTestutils.simple_tcpv6_packet(*a, **kw)


def simple_udp_packet(*a, **kw):
    return ptfTestutils.simple_udp_packet(*a, **kw)


def simple_udpv6_packet(*a, **kw):
    return ptfTestutils.simple_udpv6_packet(*a, **kw)


def simple_vxlan_packet(*a, **kw):
    return ptfTestutils.simple_vxlan_packet(*a, **kw)


def simple_vxlanv6_packet(*a, **kw):
    return ptfTestutils.simple_vxlanv6_packet(*a, **kw)


@dataplane_redirect
def send_packet(test, port_id, pkt, count=1):
    pass


@dataplane_redirect
def verify_packets(test, pkt, ports=[], device_number=0, timeout=None, n_timeout=None):
    pass


@dataplane_redirect
def verify_packet(test, pkt, port_id, timeout=None):
    pass

@dataplane_redirect
def verify_no_packet(test, pkt, port_id, timeout=None):
    pass

@dataplane_redirect
def verify_no_other_packets(test, device_number=0, timeout=None):
    pass

@dataplane_redirect
def verify_any_packet_any_port(test, pkts=[], ports=[], device_number=0, timeout=None, n_timeout=None):
    pass

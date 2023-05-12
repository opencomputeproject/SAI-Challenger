import datetime
import logging

import dpkt
from saichallenger.common.sai_dataplane.sai_dataplane import SaiDataPlane
from snappi import snappi

BASE_TENGINE_PORT = 5555

class SaiSnappiDataPlane(SaiDataPlane):

    def __init__(self, cfg):
        self.alias = cfg['alias']
        self.mode = cfg['mode']
        super().__init__(cfg)
        self.flows = []

    def init(self):
        # Configure a new API instance where the location points to controller
        # Ixia-C:       location = "https://<tgen-ip>:<port>"
        # IxNetwork:    location = "https://<tgen-ip>:<port>", ext="ixnetwork"
        # TRex:         location =         "<tgen-ip>:<port>", ext="trex"
        if self.mode == 'ixnet':
            self.api = snappi.api(location=self.config['controller'], verify=False, ext='ixnetwork')
        elif self.mode == 'trex':
            self.api = snappi.api(location=self.config['controller'], verify=False, ext='trex')
        else:
            self.api = snappi.api(location=self.config['controller'], verify=False)
        logging.info(f"{datetime.datetime.now().strftime('%s')} Starting connection to controller... ")

        # Create an empty configuration to be pushed to controller
        self.configuration = self.api.config()

        # Configure two ports where the location points to the port location:
        # Ixia-C:       port.location = "localhost:5555"
        # IxNetwork:    port.location = "<chassisip>;card;port"
        # TRex:         port.location = "localhost:5555"
        for pid, port in enumerate(self.config['port_groups']):
            if self.mode == 'ixnet':
                location = port['location']
                self.configuration.ports.port(name=port["name"], location=location)
            else:
                location = port.get('location', f"localhost:{BASE_TENGINE_PORT+pid}")
                self.configuration.ports.port(name=port["name"], location=location)

        cap = self.configuration.captures.capture(name="c1")[-1]
        cap.port_names = [p.name for p in self.configuration.ports]
        cap.format = cap.PCAP

        self.dataplane = self

    def deinit(self):
        pass

    def setup(self):
        self.set_config()
        self.start_capture()

    def teardown(self):
        self.stop_capture()
        self.configuration.flows.clear()
        self.flows.clear()

    @staticmethod
    def api_results_ok(results):
        if hasattr(results, 'warnings'):
            return True
        else:
            print(f'Results={results}')
            return False

    @staticmethod
    def check_warnings(response):
        if response.warnings:
            print("Warning: %s" % str(response.warnings))

    @staticmethod
    def get_capture_port_names(cfg):
        """
        Returns name of ports for which capture is enabled.
        """
        names = []
        for cap in cfg.captures:
            if cap.port_names:
                for name in cap.port_names:
                    if name not in names:
                        names.append(name)
        return names

    def set_config(self, return_time=False):
        start = datetime.datetime.now()
        try:
            logging.info("Setting config ...")
            res = self.api.set_config(self.configuration)
            if res and res.warnings:
                for warn in res.warnings:
                    logging.warning(f"Warning in set_config: {warn}")
        finally:
            elapsed = (datetime.datetime.now() - start).microseconds * 1000
            logging.info("Elapsed duration %s: %d ms", "set_config", elapsed)
        if return_time:
            return elapsed

    def start_capture(self):
        """ Start a capture which was already configured.
        """
        capture_names = self.get_capture_port_names(self.configuration)
        logging.info(f"Starting capture on ports {str(capture_names)}")
        cs = self.api.capture_state()
        cs.state = cs.START
        self.check_warnings(self.api.set_capture_state(cs))

    def stop_capture(self):
        capture_names = self.get_capture_port_names(self.configuration)
        logging.info(f"Stopping capture on ports {str(capture_names)}")
        cs = self.api.capture_state()
        cs.state = cs.STOP
        self.check_warnings(self.api.set_capture_state(cs))

    def get_all_captures(self):
        """
        Returns a dictionary where port name is the key and value is a list of
        frames where each frame is represented as a list of bytes.
        """
        cap_dict = {}
        for name in self.get_capture_port_names(self.configuration):
            print("Fetching captures from port %s" % name)
            request = self.api.capture_request()
            request.port_name = name
            pcap_bytes = self.api.get_capture(request)

            cap_dict[name] = []
            for ts, pkt in dpkt.pcap.Reader(pcap_bytes):
                cap_dict[name].append(list(pkt))

        return cap_dict

    def start_traffic(self, flow_names=None):
        """ Start traffic flow(s) which are already configured.
        """
        ts = self.api.transmit_state()
        ts.state = ts.START
        if flow_names is not None:
            ts.flow_names = flow_names
            logging.info(f'Start flows: {" ".join(flow_names)}')
        else:
            logging.info('Start traffic')
        res = self.api.set_transmit_state(ts)
        assert self.api_results_ok(res), res

    def stop_traffic(self):
        """ Stop traffic flow(s) which are already configured.
        """
        ts = self.api.transmit_state()
        ts.state = ts.STOP
        logging.info('Stop traffic')
        res = self.api.set_transmit_state(ts)
        assert self.api_results_ok(res), res

    # PAUSE api not supported by Ixia-C
    def pause_traffic(self):
        """ Pause traffic flow(s) which are already configured.
        """
        ts = self.api.transmit_state()
        ts.state = ts.PAUSE
        logging.info('Pause traffic')
        res = self.api.set_transmit_state(ts)
        assert self.api_results_ok(res), res

    def is_traffic_stopped(self, flow_names=[]):
        """
        Returns true if traffic in stop state
        """
        fq = self.api.metrics_request()
        fq.flow.flow_names = flow_names
        metrics = self.api.get_metrics(fq).flow_metrics
        return all([m.transmit == "stopped" for m in metrics])

    def get_all_stats(self, print_output=True):
        """
        Returns all port and flow stats
        """
        print("Fetching all port stats ...")
        request = self.api.metrics_request()
        request.port.port_names = []
        port_results = self.api.get_metrics(request).port_metrics
        if port_results is None:
            port_results = []

        # print("Fetching all flow stats ...")
        # request = self.api.metrics_request()
        # request.choice = request.FLOW
        # request.flow
        # flow_results = self.api.get_metrics(request).flow_metrics
        # if flow_results is None:
        #     flow_results = []

        # if print_output:
        #     print_stats(port_stats=port_results, flow_stats=flow_results)

        return port_results

    def stats_ok(self, packets):
        """
        Returns true if stats are as expected, false otherwise.
        """
        _, flow_stats = self.get_all_stats()

        flow_rx = sum([f.frames_rx for f in flow_stats])
        return flow_rx == packets

    def add_flow(self,
                 name,
                 packet_count=1,
                 seconds_count=0,
                 pps=10,
                 force_pps=False
                 ):

        name = name or f"flow_{datetime.datetime.now().timestamp()}"
        flow = self.configuration.flows.flow(name=name)[-1]

        flow.tx_rx.port.tx_name = self.configuration.ports[0].name
        flow.tx_rx.port.rx_name = self.configuration.ports[0].name

        if (seconds_count > 0):
            flow.duration.fixed_seconds.seconds = seconds_count
        else:
            flow.duration.fixed_packets.packets = packet_count

        flow.size.fixed = 128
        flow.metrics.enable = True

        flow.rate.pps = pps

        self.flows.append(flow)
        return flow

    def set_increment(self, field, choice, count, start, step):
        if choice == 'increment':
            field.choice = choice
            field.increment.count = count
            field.increment.start = start
            field.increment.step = step

    def add_ethernet_header(self,
                            flow: snappi.Flow,
                            dst_mac="FF:FF:FF:FF:FF:FF",
                            src_mac="00:01:02:03:04:05",
                            eth_type=0x0800,
                            dst_choice=snappi.PatternFlowEthernetDst.VALUE,
                            dst_count=1,
                            dst_step="00:00:00:00:00:01",
                            src_choice=snappi.PatternFlowEthernetSrc.VALUE,
                            src_count=1,
                            src_step="00:00:00:00:00:01"
                            ):
        if flow == None:
            return None

        ether = flow.packet.add().ethernet
        if dst_count == 1:
            # Setup fixed value
            ether.dst.value = dst_mac
        else:
            # Setup increment
            self.set_increment(ether.dst, dst_choice, dst_count, dst_mac, dst_step)
        if src_count == 1:
            # Setup fixed value
            ether.src.value = src_mac
        else:
            # Setup increment
            self.set_increment(ether.src, src_choice, src_count, src_mac, src_step)
        ether.ether_type.value = eth_type

        return ether

    # TODO: add other fields
    def add_ipv4_header(self,
                        flow: snappi.Flow,
                        dst_ip="192.168.0.1",
                        src_ip="192.168.0.2",
                        dst_choice=snappi.PatternFlowIpv4Dst.VALUE,
                        dst_count=1,
                        dst_step="0.0.0.1",
                        src_choice=snappi.PatternFlowIpv4Src.VALUE,
                        src_count=1,
                        src_step="0.0.0.1"
                        ):
        if flow == None:
            return None

        ipv4 = flow.packet.add().ipv4
        ipv4.dst.value = dst_ip
        ipv4.src.value = src_ip

        # Setup increment
        self.set_increment(ipv4.dst, dst_choice, dst_count, dst_ip, dst_step)
        self.set_increment(ipv4.src, src_choice, src_count, src_ip, src_step)

        return ipv4

    def add_udp_header(self,
                        flow: snappi.Flow,
                        dst_port=80,
                        src_port=1234,
                        dst_choice=snappi.PatternFlowUdpDstPort.VALUE,
                        dst_count=1,
                        dst_step=1,
                        src_choice=snappi.PatternFlowUdpSrcPort.VALUE,
                        src_count=1,
                        src_step=1
                        ):
        if flow == None:
            return None

        udp = flow.packet.add().udp
        udp.dst_port.value = dst_port
        udp.src_port.value = src_port

        # Setup increment
        self.set_increment(udp.dst_port, dst_choice, dst_count, dst_port, dst_step)
        self.set_increment(udp.src_port, src_choice, src_count, src_port, src_step)

        return udp

    def add_vxlan_header(self,
                        flow: snappi.Flow,
                        vni=100,
                        vni_choice=snappi.PatternFlowVxlanVni.VALUE,
                        vni_count=1,
                        vni_step=1
                        ):
        if flow == None:
            return None

        vxlan = flow.packet.add().vxlan
        vxlan.vni.value = vni
        # Other supported fields. Uncomment in case of emergency ;)
        # vxlan.flags.value = 0b00001000  # VNI is True
        # vxlan.reserved0.value = 0
        # vxlan.reserved1.value = 0

        # Setup increment
        self.set_increment(vxlan.vni, vni_choice, vni_count, vni, vni_step)

        return vxlan

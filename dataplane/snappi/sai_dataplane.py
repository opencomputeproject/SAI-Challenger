
import logging
import sys
import time

import dpkt
from saichallenger.common.sai_dataplane import SaiDataplane
from snappi import snappi

BASE_TENGINE_PORT = 5555
DEFAULT_STEP = 0.2
DEFAULT_TIMEOUT = 2
DEFAULT_N_TIMEOUT = 2


def seconds_elapsed(start_seconds):
    return int(round(time.time() - start_seconds))


def timed_out(start_seconds, timeout):
    return seconds_elapsed(start_seconds) > timeout


def wait_for(func, condition_str, interval_seconds=None, timeout_seconds=None):
    """
    Keeps calling the `func` until it returns true or `timeout_seconds` occurs
    every `interval_seconds`. `condition_str` should be a constant string
    implying the actual condition being tested.
    Usage
    -----
    If we wanted to poll for current seconds to be divisible by `n`, we would
    implement something similar to following:
    ```
    import time
    def wait_for_seconds(n, **kwargs):
        condition_str = 'seconds to be divisible by %d' % n
        def condition_satisfied():
            return int(time.time()) % n == 0
        poll_until(condition_satisfied, condition_str, **kwargs)
    ```
    """
    if interval_seconds is None:
        interval_seconds = DEFAULT_STEP
    if timeout_seconds is None:
        timeout_seconds = DEFAULT_TIMEOUT
    start_seconds = int(time.time())

    print("\n\nWaiting for %s ..." % condition_str)
    while True:
        res = func()
        if res:
            print("Done waiting for %s" % condition_str)
            break
        if res is None:
            raise Exception("Wait aborted for %s" % condition_str)
        if timed_out(start_seconds, timeout_seconds):
            msg = "Time out occurred while waiting for %s" % condition_str
            raise Exception(msg)

        time.sleep(interval_seconds)


class SaiDataplaneImpl(SaiDataplane):

    def __init__(self, exec_params):
        self.alias = exec_params['alias']
        self.mode = exec_params['mode']
        super().__init__(exec_params)

    def init(self):
        # Configure a new API instance where the location points to controller
        # Ixia-C:       location = "https://<tgen-ip>:<port>"
        # IxNetwork:    location = "https://<tgen-ip>:<port>", ext="ixnetwork"
        # TRex:         location =         "<tgen-ip>:<port>", ext="trex"
        if self.mode == 'ixnet':
            self.api = snappi.api(location=self.exec_params['controller'], verify=False, ext='ixnetwork')
        elif self.mode == 'trex':
            self.api = snappi.api(location=self.exec_params['controller'], verify=False, ext='trex')
        else:
            self.api = snappi.api(location=self.exec_params['controller'], verify=False)
        logging.info("%s Starting connection to controller... " % time.strftime("%s"))

        # Create an empty configuration to be pushed to controller
        self.configuration = self.api.config()

        # Configure two ports where the location points to the port location:
        # Ixia-C:       port.location = "localhost:5555"
        # IxNetwork:    port.location = "<chassisip>;card;port"
        # TRex:         port.location = "localhost:5555"
        for pid, port in enumerate(self.exec_params['port_groups']):
            location = port.get('location', f"localhost:{BASE_TENGINE_PORT+pid}")
            self.configuration.ports.port(name=port[port['init']], location=location)

        cap = self.configuration.captures.capture(name="c1")[-1]
        cap.port_names = [p.name for p in self.configuration.ports]
        cap.format = cap.PCAP

        self.dataplane = self

    def remove(self):
        pass

    def setUp(self):
        super().setUp()
        self.set_config()
        self.start_capture()

    def tearDown(self):
        super().tearDown()
        self.stop_capture()
        self.configuration.flows.clear()

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
            if cap._properties.get("port_names"):
                for name in cap.port_names:
                    if name not in names:
                        names.append(name)
        return names

    def set_config(self, return_time=False):
        start_time = time.time()
        logging.info('Setting config ...')
        res = self.api.set_config(self.configuration)
        assert self.api_results_ok(res), res
        if len(res.warnings) > 0:
            logging.info('Warnings in set_config : {}'.format(res.warnings))
        end_time = time.time()
        operation_time = (end_time - start_time) * 1000
        if return_time:
            return operation_time

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
                if sys.version_info[0] == 2:
                    cap_dict[name].append([ord(b) for b in pkt])
                else:
                    cap_dict[name].append(list(pkt))

        return cap_dict

    def start_traffic(self):
        """ Start traffic flow(s) which are already configured.
        """
        ts = self.api.transmit_state()
        ts.state = ts.START
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
        request.choice = request.PORT
        request.port
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

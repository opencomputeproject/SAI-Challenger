class SaiDataPlane():
    """
    Base class for SAI dataplane implementations.

    Provides interface for packet transmission and reception in SAI test scenarios.
    """
    def __init__(self, cfg):
        self.config = cfg
        # used by dataplane_redirect() from ptf_testutils
        self.driver = cfg["type"] if cfg is not None else "ptf"

    def init(self):
        """
        per session init
        """
        pass

    def deinit(self):
        """
        per session deinit
        """
        pass

    def setup(self):
        """
        per testcase setup
        """
        pass

    def teardown(self):
        """
        per testcase teardown
        """
        pass

    @staticmethod
    def spawn(params) -> 'SaiDataPlane':
        """Spawn dataplane implementation based on the parameters"""

        if params["type"] == "ptf":
            from sai_dataplane.ptf.sai_ptf_dataplane import SaiPtfDataPlane
            dataplane = SaiPtfDataPlane(params)
        elif params["type"] == "snappi":
            from sai_dataplane.snappi.sai_snappi_dataplane import SaiSnappiDataPlane
            dataplane = SaiSnappiDataPlane(params)
        else:
            raise RuntimeError("Appropriate driver wasn't found")
        return dataplane
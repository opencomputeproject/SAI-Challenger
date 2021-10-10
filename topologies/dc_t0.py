from contextlib import contextmanager
import pytest
from sai import SaiObjType


@contextmanager
def config(npu):
    topo_cfg = {

    }
    
    # SETUP
    yield topo_cfg
    # TEARDOWN


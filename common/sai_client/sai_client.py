import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class SaiClient:
    """SAI client interface to wrap low level SAI calls. Is used to define own SAI wrappers"""
    def __init__(self, client_config):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError

    def set_loglevel(self, sai_api, loglevel):
        raise NotImplementedError

    # CRUD
    def create(self, obj_type, *, key=None, attrs=None, do_assert=True):
        """
        Create SAI object of appropriate object type. Key has to be provided if object doesn't care oid.
        if do_assert is set to False unsuccessful operation silently fails
        """

        raise NotImplementedError

    def remove(self, *, oid=None, obj_type=None, key=None, do_assert=True):
        """
        Remove SAI object by oid or by key
        if do_assert is set to False unsuccessful operation silently fails
        """
        raise NotImplementedError

    def set(self, *, oid=None, obj_type=None, key=None, attr=None, do_assert=True):
        """
        Set attribute for SAI object.
        if do_assert is set to False unsuccessful operation silently fails
        """
        raise NotImplementedError

    def get(self, *, oid=None, obj_type=None, key=None, attrs=None, do_assert=True):
        """
        Get attributes for SAI object.
        if do_assert is set to False unsuccessful operation silently fails
        """
        raise NotImplementedError

    # Stats
    def get_stats(self, oid=None, obj_type=None, key=None, attrs=None):
        raise NotImplementedError

    def clear_stats(self, oid=None, obj_type=None, key=None, attrs=None):
        raise NotImplementedError

    # Flush FDB
    def flush_fdb_entries(self, attrs=None):
        raise NotImplementedError

    # BULK
    def bulk_create(self, obj_type, keys=None, attrs=None):
        raise NotImplementedError

    def bulk_remove(self, oids=None, obj_type=None, keys=None):
        raise NotImplementedError

    def bulk_set(self, oids=None, obj_type=None, keys=None, attrs=None):
        raise NotImplementedError

    # Host interface
    def remote_iface_exists(self, iface):
        raise NotImplementedError

    def remote_iface_is_up(self, iface):
        raise NotImplementedError

    def remote_iface_status_set(self, iface, status):
        raise NotImplementedError

    def remote_iface_agent_start(self, ifaces):
        raise NotImplementedError

    def remote_iface_agent_stop(self):
        raise NotImplementedError

    @staticmethod
    def build(params) -> 'SaiClient':
        """Load different SAI client implementations based on parameters"""
        # TODO move to loading different implementations by using python entrypoints mechanism
        if params["type"] == "redis":
            from sai_client.sai_redis_client.sai_redis_client import SaiRedisClient
            sai_client = SaiRedisClient(params["config"])
        elif params["type"] == "thrift":
            from sai_client.sai_thrift_client.sai_thrift_client import SaiThriftClient
            sai_client = SaiThriftClient(params["config"])
        else:
            raise RuntimeError("Appropriate driver wasn't found")
        return sai_client

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

    def apply_rec(self, fname):
        raise NotImplementedError

    # CRUD
    def create(self, obj, attrs, do_assert=True):
        """
        Create SAI object of appropriate object type.
        if do_assert is set to False unsuccessful operation silently fails
        """

        raise NotImplementedError

    def remove(self, obj, do_assert=True):
        """
        Remove SAI object by oid or by key
        if do_assert is set to False unsuccessful operation silently fails
        """
        raise NotImplementedError

    def set(self, obj, attr, do_assert=True):
        """
        Set attribute for SAI object.
        if do_assert is set to False unsuccessful operation silently fails
        """
        raise NotImplementedError

    def get(self, obj, attrs, do_assert=True):
        """
        Get attributes for SAI object.
        if do_assert is set to False unsuccessful operation silently fails
        """
        raise NotImplementedError

    # Stats
    def get_stats(self, obj, attrs, do_assert=True):
        raise NotImplementedError

    def clear_stats(self, obj, attrs, do_assert=True):
        raise NotImplementedError

    # Flush FDB
    def flush_fdb_entries(self, obj, attrs=None):
        raise NotImplementedError

    # BULK
    def bulk_create(self, obj, keys, attrs, do_assert=True):
        raise NotImplementedError

    def bulk_remove(self, obj, keys, do_assert=True):
        raise NotImplementedError

    def bulk_set(self, obj, keys, attrs, do_assert=True):
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

    # Generic
    def get_object_key(self, obj_type=None):
        '''
        Returns a dictionary where object type is a key,
        and the list of SAI object keys (OIDs or entries) is a value.
        '''
        raise NotImplementedError

    @staticmethod
    def spawn(params) -> 'SaiClient':
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

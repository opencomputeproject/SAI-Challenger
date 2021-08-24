import json
import time
from sai import Sai
from sai import SaiData
from sai import SaiObjType
from sai_dataplane import SaiDataPlane
from sai_dataplane import SaiHostifDataPlane


class SaiNpu(Sai):

    def __init__(self, exec_params):
        super().__init__(exec_params)

        self.oid = "oid:0x0"
        self.dot1q_br_oid = "oid:0x0"
        self.default_vlan_oid = "oid:0x0"
        self.default_vlan_id = "0"
        self.default_vrf_oid = "oid:0x0"
        self.port_oids = []
        self.dot1q_bp_oids = []
        self.hostif_dataplane = None
        self.hostif_map = None

    def init(self, attr):
        self.port_oids.clear()
        self.dot1q_bp_oids.clear()

        sw_attr = attr.copy()
        sw_attr.append("SAI_SWITCH_ATTR_INIT_SWITCH")
        sw_attr.append("true")
        sw_attr.append("SAI_SWITCH_ATTR_TYPE")
        sw_attr.append("SAI_SWITCH_TYPE_NPU")

        self.oid = self.create(SaiObjType.SWITCH, sw_attr)
        self.rec2vid[self.oid] = self.oid

        # Default .1Q bridge
        self.dot1q_br_oid = self.get(self.oid, ["SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID", "oid:0x0"]).oid()
        assert (self.dot1q_br_oid != "oid:0x0")

        # Default VLAN
        self.default_vlan_oid = self.get(self.oid, ["SAI_SWITCH_ATTR_DEFAULT_VLAN_ID", "oid:0x0"]).oid()
        assert (self.default_vlan_oid != "oid:0x0")

        self.default_vlan_id = self.get(self.default_vlan_oid, ["SAI_VLAN_ATTR_VLAN_ID", ""]).to_json()[1]
        assert (self.default_vlan_id != "0")

        # Default VRF
        self.default_vrf_oid = self.get(self.oid, ["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID", "oid:0x0"]).oid()
        assert (self.default_vrf_oid != "oid:0x0")

        # Ports
        port_num = self.get(self.oid, ["SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS", ""]).uint32()
        if port_num > 0:
            self.port_oids = self.get(self.oid,
                                     ["SAI_SWITCH_ATTR_PORT_LIST", self.make_list(port_num, "oid:0x0")]).oids()

            # .1Q bridge ports
            status, data = self.get(self.dot1q_br_oid, ["SAI_BRIDGE_ATTR_PORT_LIST", "1:oid:0x0"], False)
            bport_num = data.uint32()
            assert (status == "SAI_STATUS_BUFFER_OVERFLOW")
            assert (bport_num > 0)

            self.dot1q_bp_oids = self.get(self.dot1q_br_oid,
                                         ["SAI_BRIDGE_ATTR_PORT_LIST", self.make_list(bport_num, "oid:0x0")]).oids()
            assert (bport_num == len(self.dot1q_bp_oids))

    def reset(self):
        self.cleanup()
        time.sleep(5)
        attr = []
        self.init(attr)

    def flush_fdb_entries(self, attrs):
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate("SAI_OBJECT_TYPE_SWITCH:" + self.oid, attrs, "Sflush")
        assert status[0].decode("utf-8") == 'Sflushresponse'
        assert status[2].decode("utf-8") == 'SAI_STATUS_SUCCESS'

    def clear_stats(self, obj, attrs, do_assert = True):
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sclear_stats")    
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'
        return status[2]

    def get_stats(self, obj, attrs, do_assert = True):
        if obj.startswith("oid:"):
            obj = self.vid_to_type(obj) + ":" + obj
        if type(attrs) != str:
            attrs = json.dumps(attrs)
        status = self.operate(obj, attrs, "Sget_stats")
        status[2] = status[2].decode("utf-8")
        if do_assert:
            assert status[2] == 'SAI_STATUS_SUCCESS'

        data = SaiData(status[1].decode("utf-8"))
        if do_assert:
            return data

        return status[2], data 

    def __bulk_attr_serialize(self, attr):
        data = ""
        # Input attributes: [a, v, a, v, ...]
        # Serialized attributes format: "a=v|a=v|..."
        for i, v in enumerate(attr):
            if i % 2 == 0:
                if len(data) > 0:
                    data += "|"
                data += v + "="
            else:
                data += v
        return data

    def bulk_create(self, obj, keys, attrs, do_assert = True):
        '''
        Bulk create FDB/route objects

        Parameters:
            obj (SaiObjType): The type of objects to be created
            keys (list): The list of objects to be created.
                    E.g.:
                    [
                        {
                            "bvid"      : vlan_oid,
                            "mac"       : "00:00:00:00:00:01",
                            "switch_id" : self.sw_oid
                        },
                        {...}
                    ]
            attrs (list): The list of the lists of objects' attributes.
                    In case just one set of the attributes provided, all objects
                    will be created with this set of the attributes.
                    E.g.:
                    [
                        [
                            "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                            "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", self.sw.dot1q_bp_oids[0]
                        ],
                        [...]
                    ]
            do_assert (bool): Assert that the bulk create operation succeeded.

        Usage example:
            bulk_create(SaiObjType.FDB_ENTRY, [key1, key2, ...], [attrs1, attrs2, ...])
            bulk_create(SaiObjType.FDB_ENTRY, [key1, key2, ...], [attrs])

            where, attrsN = [attr1, val1, attr2, val2, ...]

        Returns:
            The tuple with two elements.
            The first element contains bulk create operation status:
                * "SAI_STATUS_SUCCESS" on success when all objects were created;
                * "SAI_STATUS_FAILURE" when any of the objects fails to create;
            The second element contains the list of statuses of each individual object
            creation result.
        '''
        assert type(obj) == SaiObjType
        assert obj == SaiObjType.FDB_ENTRY or obj == SaiObjType.ROUTE_ENTRY
        assert len(keys) == len(attrs) or len(attrs) == 1

        str_attr = ""
        if (len(attrs) == 1):
            str_attr = self.__bulk_attr_serialize(attrs[0])

        key = "SAI_OBJECT_TYPE_" + obj.name + ":" + str(len(keys))
        values = []
        for i, _ in enumerate(keys):
            values.append(json.dumps(keys[i]))
            if (len(attrs) > 1):
                str_attr = self.__bulk_attr_serialize(attrs[i])
            values.append(str_attr)

        status = self.operate(key, json.dumps(values), "Sbulkcreate")

        status[1] = status[1].decode("utf-8")
        status[1] = json.loads(status[1])
        entry_status = []
        for i, v in enumerate(status[1]):
            if i % 2 == 0:
                entry_status.append(v)

        status[2] = status[2].decode("utf-8")

        if do_assert:
            print(entry_status)
            assert status[2] == 'SAI_STATUS_SUCCESS'
            return status[2], entry_status

        return status[2], entry_status

    def bulk_remove(self, obj, keys, do_assert = True):
        '''
        Bulk remove FDB/route objects

        Parameters:
            obj (SaiObjType): The type of objects to be removed
            keys (list): The list of objects to be removed.
                    E.g.:
                    [
                        {
                            "bvid"      : vlan_oid,
                            "mac"       : "00:00:00:00:00:01",
                            "switch_id" : self.sw_oid
                        },
                        {...}
                    ]
            do_assert (bool): Assert that the bulk remove operation succeeded.

        Usage example:
            bulk_remove(SaiObjType.FDB_ENTRY, [key1, key2, ...])
            bulk_remove(SaiObjType.FDB_ENTRY, [key1, key2, ...], False)

        Returns:
            The tuple with two elements.
            The first element contains bulk remove operation status:
                * "SAI_STATUS_SUCCESS" on success when all objects were removed;
                * "SAI_STATUS_FAILURE" when any of the objects fails to remove;
            The second element contains the list of statuses of each individual object
            removal result.
        '''
        assert type(obj) == SaiObjType
        assert obj == SaiObjType.FDB_ENTRY or obj == SaiObjType.ROUTE_ENTRY

        key = "SAI_OBJECT_TYPE_" + obj.name + ":" + str(len(keys))
        values = []
        for i, v in enumerate(keys):
            values.append(json.dumps(v))
            values.append("")

        status = self.operate(key, json.dumps(values), "Dbulkremove")

        status[1] = status[1].decode("utf-8")
        status[1] = json.loads(status[1])
        entry_status = []
        for i, v in enumerate(status[1]):
            if i % 2 == 0:
                entry_status.append(v)

        status[2] = status[2].decode("utf-8")

        if do_assert:
            print(entry_status)
            assert status[2] == 'SAI_STATUS_SUCCESS'
            return status[2], entry_status

        return status[2], entry_status

    def create_fdb(self, vlan_oid, mac, bp_oid, action = "SAI_PACKET_ACTION_FORWARD"):
        self.create('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.oid
                       }
                   ),
                   [
                       "SAI_FDB_ENTRY_ATTR_TYPE",           "SAI_FDB_ENTRY_TYPE_STATIC",
                       "SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID", bp_oid,
                       "SAI_FDB_ENTRY_ATTR_PACKET_ACTION",  action
                   ])

    def remove_fdb(self, vlan_oid, mac):
        self.remove('SAI_OBJECT_TYPE_FDB_ENTRY:' + json.dumps(
                       {
                           "bvid"      : vlan_oid,
                           "mac"       : mac,
                           "switch_id" : self.oid
                       })
                   )

    def create_vlan_member(self, vlan_oid, bp_oid, tagging_mode):
        oid = self.create(SaiObjType.VLAN_MEMBER,
                    [
                        "SAI_VLAN_MEMBER_ATTR_VLAN_ID",           vlan_oid,
                        "SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID",    bp_oid,
                        "SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE", tagging_mode
                    ])
        return oid

    def remove_vlan_member(self, vlan_oid, bp_oid):
        assert vlan_oid.startswith("oid:")

        vlan_mbr_oids = []
        status, data = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST", "1:oid:0x0"], False)
        if status == "SAI_STATUS_SUCCESS":
            vlan_mbr_oids = data.oids()
        elif status == "SAI_STATUS_BUFFER_OVERFLOW":
            oids = self.make_list(data.uint32(), "oid:0x0")
            vlan_mbr_oids = self.get(vlan_oid, ["SAI_VLAN_ATTR_MEMBER_LIST", oids]).oids()
        else:
            assert status == "SAI_STATUS_SUCCESS"

        for vlan_mbr_oid in vlan_mbr_oids:
            oid = self.get(vlan_mbr_oid, ["SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID", "oid:0x0"]).oid()
            if oid == bp_oid:
                self.remove(vlan_mbr_oid)
                return

        assert False

    def hostif_dataplane_start(self, ifaces):
        self.hostif_map = dict()

        # Start ptf_nn_agent.py on DUT
        if self.remote_iface_agent_start(ifaces) == False:
            return None

        for inum, iname in ifaces.items():
            socket_addr = 'tcp://{}:10001'.format(self.server_ip)
            self.hostif_map[(0, int(inum))] = socket_addr

        self.hostif_dataplane = SaiHostifDataPlane(ifaces, self.server_ip)
        self.hostif_dataplane.init()
        return self.hostif_dataplane

    def hostif_dataplane_stop(self):
        self.dataplane_pkt_listen()
        self.hostif_map = None
        self.hostif_dataplane.deinit()
        self.hostif_dataplane = None
        return self.remote_iface_agent_stop()

    def hostif_pkt_listen(self):
        self.port_map = SaiDataPlane.getPortMap()
        SaiDataPlane.setPortMap(self.hostif_map)

    def dataplane_pkt_listen(self):
        self.hostif_map = SaiDataPlane.getPortMap()
        SaiDataPlane.setPortMap(self.port_map)
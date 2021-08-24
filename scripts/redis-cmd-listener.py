#!/usr/bin/env python

import redis
import time
import json
import os
import socket
import struct
from fcntl import ioctl
import subprocess
import logging

SIOCGIFFLAGS   = 0x8913          # get the active flag word of the device
SIOCSIFFLAGS   = 0x8914          # set the active flag word of the device
IFF_UP         = 0x0001

logging.basicConfig(format='%(message)s')
logger = logging.getLogger('ptf_nn_agent')


def iface_exists(iface_name):
    return iface_name in os.listdir('/sys/class/net')


def iface_is_up(iface_name):
    try:
        s = socket.socket()
        ifr = struct.pack('16sh', str.encode(iface_name), 0)
        result = ioctl(s, SIOCGIFFLAGS, ifr)
        s.close()
    except:
        return False

    flags = struct.unpack('16sh', result)[1]
    return flags & IFF_UP > 0


def set_iface_status(args):
    iface_name = args["iface"]
    s = socket.socket()
    ifr = struct.pack('16sh', str.encode(iface_name), 0)
    result = ioctl(s, SIOCGIFFLAGS, ifr)
    flags = struct.unpack('16sh', result)[1]
    if args["admin"] == "up":
       flags |= IFF_UP
    else:
       flags &= ~IFF_UP
    ifr = struct.pack('16sh', str.encode(iface_name), flags)
    ioctl(s, SIOCSIFFLAGS, ifr)
    s.close()
    return True


def start_nn_agent(ifaces):
    iface_args = ""
    nn_agent_cmd = ["ptf_nn_agent.py", "--device-socket", "0@tcp://0.0.0.0:10001"]
    logger.info(ifaces)
    for inum, iname in ifaces.items():
        #if not iface_is_up(iname):
        #    return None
        nn_agent_cmd.append("-i")
        nn_agent_cmd.append("{}@{}".format(inum, iname))
    logger.info(str(nn_agent_cmd))
    p = subprocess.Popen(nn_agent_cmd)
    return p


def process_is_running(p):
    return p is not None and p.returncode is None


def stop_process(p):
    if p:
        p.terminate()
        p.wait()
    return p.returncode is not None


def main():
    logger.setLevel(logging.INFO)

    nn_agent_p = None
    time.sleep(5)
    r = redis.Redis(host='localhost', port=6379, db=1)
    while True:
        cmd = r.lrange("SAI_CHALLENGER_CMD_QUEUE", 0, -1)
        if len(cmd) == 0:
            time.sleep(0.2)
            continue

        logger.info(cmd)
        r.delete("SAI_CHALLENGER_CMD_QUEUE")

        for i in range(len(cmd)):
            cmd[i] = cmd[i].decode("utf-8")

        if cmd[0] == "iface_exists" and len(cmd) == 2:
            status = "ok" if iface_exists(cmd[1]) else "err"
        elif cmd[0] == "iface_is_up" and len(cmd) == 2:
            status = "ok" if iface_is_up(cmd[1]) else "err"
        elif cmd[0] == "set_iface_status" and len(cmd) == 2:
            status = "ok" if set_iface_status(json.loads(cmd[1])) else "err"
        elif cmd[0] == "start_nn_agent" and len(cmd) == 2:
            nn_agent_p = start_nn_agent(json.loads(cmd[1]))
            status = "ok" if process_is_running(nn_agent_p) else "err"
        elif cmd[0] == "stop_nn_agent":
            if stop_process(nn_agent_p) == True:
                nn_agent_p = None
                status = "ok"
            else:
                status = "err"
        else:
            status = "err"

        logger.info(status)
        r.lpush("SAI_CHALLENGER_CMD_STATUS_QUEUE", status)


if __name__ == "__main__":
    main()


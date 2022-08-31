import time

default_step = 0.2
default_timeout = 2
default_n_timeout = 2


def pcap_bts_polling(func, func_arg, timeout=None, step=None):
    if timeout is None:
        timeout = default_timeout
    if step is None:
        step = default_step

    end_time = time.time() + timeout
    while True:
        pcap_bts = func(func_arg)
        if len(pcap_bts.getvalue()) > 0:
            return pcap_bts
        time.sleep(step)
        if time.time() > end_time:
            return pcap_bts


def print_pkts_side_by_side(p1, p2):
    """ Utility to print out two packets' contents as side-by-side bytes"""
    exl = len(p1)
    bex = bytes(p1)
    rxl = len(p2)
    brx = bytes(p2)
    maxlen = rxl if rxl > exl else exl

    print("Byte#\t Exp \t Eq?\t Rx\n")
    for i in range(maxlen):
        if i < exl and i < rxl:
            print("[%d]\t %02x\t %s\t %02x" % (i, bex[i], "==" if brx[i] == bex[i] else "!=", brx[i]))
        elif i < exl:
            print("[%d]\t %02x\t %s\t %s" % (i, bex[i], "!=", "--"))
        else:
            print("[%d]\t %s\t %s\t %02x" % (i, "--", "!=", brx[i]))


def pkt_layers(p):
    layers = []
    layer_num = 0
    while True:
        layer = p.getlayer(layer_num)
        if layer is not None:
            layers.append(layer.name)
        else:
            break
        layer_num += 1
    return layers


def pkt_layers_str(p):
    return ":".join(pkt_layers(p))


def compare_pkts2(pkt1, pkt2):
    """ Compare two packets
        return bool, string, masked pkt1, masked pkt2
        where bool = True if masked packets match,
        string = reason for mismatch
    """

    # make copies, blank out fields per compare flags
    p1 = pkt1.copy()
    p2 = pkt2.copy()
    l = 'Ether'
    if pkt1.haslayer(l) or pkt2.haslayer(l):
        if not pkt1.haslayer(l):
            return False, "pkt1 missing %s layer" % l, p1, p2
        if not pkt2.haslayer(l):
            return False, "pkt2 missing %s layer" % l, p1, p2
    l = 'IP'
    if pkt1.haslayer(l) or pkt2.haslayer(l):
        if not pkt1.haslayer(l):
            return False, "pkt1 missing %s layer" % l, p1, p2
        if not pkt2.haslayer(l):
            return False, "pkt2 missing %s layer" % l, p1, p2

    l = 'TCP'
    if pkt1.haslayer(l) or pkt2.haslayer(l):
        if not pkt1.haslayer(l):
            return False, "pkt1 missing %s layer" % l, p1, p2
        if not pkt2.haslayer(l):
            return False, "pkt2 missing %s layer" % l, p1, p2

    if len(pkt1) != len(pkt2):
        return False, 'unequal len: pkt1=%d,pkt2=%d' % (len(pkt1), len(pkt2)), p1, p2

    exl = len(p1)
    bex = bytes(p1)
    rxl = len(p2)
    brx = bytes(p2)
    maxlen = rxl if rxl > exl else exl

    for i in range(maxlen - 4):
        if bex[i] != brx[i]:
            print("Layers: %s != %s " % (pkt_layers_str(p1), pkt_layers_str(p1)))
            return False, "Mismatched", p1, p2

    return True, "", p1, p2

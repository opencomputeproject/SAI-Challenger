#!/usr/bin/python3

import click
import json
import os

from saichallenger.common.sai_data import SaiObjType
from saichallenger.common.sai_npu import SaiNpu

VERSION = '0.1'

exec_params = {
    # Generic parameters
    "traffic": False,
    "testbed": None,
     # DUT specific parameters
    "alias": "dut",
    "asic": None,
    "target": None,
    "sku": None,
    "client": {
        "type": "redis",
        "config": {
            "ip": "localhost",
            "port": 6379,
            "loglevel": "NOTICE",
        }
    }
}

# This is our main entrypoint - the main 'sai' command
@click.group()
def cli():
    pass


# 'init' command
@cli.command()
@click.argument('sku', metavar='[<SKU>]', required=False, type=str)
def init(sku):
    """Initialize SAI switch"""

    click.echo()

    platform = os.getenv('SC_PLATFORM')
    asic = os.getenv('SC_ASIC')
    target = os.getenv('SC_TARGET')
    asic_dir = "/sai-challenger/npu/{}/{}/".format(platform, asic)

    params = {
        # Generic parameters
        "traffic": False,
        "testbed": None,
        # DUT specific parameters
        "alias": "dut",
        "asic": asic,
        "target": target,
        "sku": sku,
        "asic_dir": asic_dir,
        "client": {
            "type": "redis",
            "config": {
                "ip": "localhost",
                "port": 6379,
                "loglevel": "NOTICE",
            }
        }
    }

    npu_mod = None
    module_name = "sai_npu"
    try:
        npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir]))
    except:
        try:
            npu_mod = imp.load_module(module_name, *imp.find_module(module_name, [asic_dir + "../"]))
        except:
            pass

    npu = npu_mod.SaiNpuImpl(params) if npu_mod is not None else SaiNpu(params)
    npu.reset()
    click.echo("Initialized {} {}\n".format(asic, target))


# 'get' command
@cli.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
@click.argument('attrs', metavar='<attr-1> .. <attr-n>', required=True, type=str, nargs=-1)
def get(oid, attrs):
    """Retrieve SAI object's attributes"""

    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    sai = SaiNpu(exec_params)

    obj_type = sai.vid_to_type(oid)
    for attr in attrs:
        attr_type = sai.get_obj_attr_type(obj_type, attr)
        if attr_type is None:
            click.echo("Unknown SAI object's attribute {}\n".format(attr))
            return False

        status, data = sai.get_by_type(oid, attr, attr_type, False)
        if status != "SAI_STATUS_SUCCESS":
            click.echo(status + '\n')
            return False

        data = data.to_json()
        click.echo("{:<48} {}".format(data[0], data[1]))

    click.echo()


# 'set' command
@cli.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
@click.argument('attr', metavar='<attr>', required=True, type=str)
@click.argument('value', metavar='<value>', required=True, type=str)
def set(oid, attr, value):
    """Set SAI object's attribute value"""

    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    if not attr.startswith("SAI_"):
        click.echo("Invalid SAI object's attribute {} provided\n".format(attr))
        return False

    sai = SaiNpu(exec_params)
    status = sai.set(oid, [attr, value], False)
    click.echo(status + '\n')


# 'create' command
@cli.command()
@click.argument('obj_type', metavar='<SAI object type>', required=True, type=str)
@click.argument('attrs', metavar='<attr> <value>', required=True, type=str, nargs=-1)
def create(obj_type, attrs):
    """Create SAI object"""

    click.echo()
    obj_type = obj_type.upper()
    try:
        obj_type = SaiObjType[obj_type]
    except KeyError:
        click.echo("Unknown SAI object type '{}'\n".format(obj_type))
        return False

    if len(attrs) % 2 != 0:
        click.echo("Invalid SAI object's attributes {} provided\n".format(attrs))
        return False

    sai = SaiNpu(exec_params)
    status, oid = sai.create(obj_type, attrs, False)
    if status == "SAI_STATUS_SUCCESS":
        click.echo("Created SAI object {} with {}\n".format(obj_type.name, oid))
    else:
        click.echo(status + '\n')


# 'remove' command
@cli.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
def remove(oid):
    """Remove SAI object"""

    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    sai = SaiNpu(exec_params)
    status = sai.remove(oid, False)
    click.echo(status + '\n')


# 'list' command
@cli.command()
@click.argument('obj_type', metavar='[<SAI object type>]', required=False, type=str)
def list(obj_type):
    """List SAI object IDs"""

    click.echo()
    if obj_type is None:
        for obj in SaiObjType:
            click.echo(obj.name.lower())
        click.echo()
        return

    obj_type = obj_type.upper()
    try:
        obj_type = SaiObjType[obj_type]
    except KeyError:
        if obj_type != "ALL":
            click.echo("Unknown SAI object type '{}'\n".format(obj_type))
            return False
        obj_type = None

    sai = SaiNpu(exec_params)

    oids = sai.get_oids(obj_type)
    for key, oids in oids.items():
        click.echo(key)
        for idx, oid in enumerate(oids):
            click.echo("{:>8})  {}".format(idx + 1, oid))
        click.echo()


# 'dump' command
@cli.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
def dump(oid):
    """ List SAI object's attribute value"""
    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    sai = SaiNpu(exec_params)
    obj_type = sai.vid_to_type(oid)
    meta = sai.get_meta(obj_type)

    for attr in meta['attributes']:
        status, data = sai.get_by_type(oid, attr['name'], attr['properties']['type'], False)
        if status == "SAI_STATUS_SUCCESS":
            data = data.to_json()
            click.echo("{:<50} {}".format(data[0], data[1]))
        else:
            click.echo("{:<50} {}".format(attr['name'], status))
    click.echo()


@cli.group()
def stats():
    """Manage SAI object's stats"""
    pass


# 'stats get' command
@stats.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
@click.argument('cntrs', metavar='<cntrs>', required=True, type=str, nargs=-1)
def get(oid, cntrs):
    """Get SAI object's stats"""

    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    sai = SaiNpu(exec_params)

    attrs = []
    for cntr in cntrs:
        attrs.append(cntr)
        attrs.append('')

    status, data = sai.get_stats(oid, attrs, False)
    if status != "SAI_STATUS_SUCCESS":
        click.echo(status + '\n')
        return False

    data = data.counters()
    for cntr in cntrs:
        click.echo("{:<48} {:>8}".format(cntr, data[cntr]))
    click.echo()


# 'stats clear' command
@stats.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
@click.argument('cntrs', metavar='<cntrs>', required=True, type=str, nargs=-1)
def clear(oid, cntrs):
    """Clear SAI object's stats"""

    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    sai = SaiNpu(exec_params)

    attrs = []
    for cntr in cntrs:
        attrs.append(cntr)
        attrs.append('')

    status = sai.clear_stats(oid, attrs, False)
    click.echo(status + '\n')


# 'version' subcommand
@cli.command()
def version():
    """Display version info"""
    click.echo("SAI CLI version {0}".format(VERSION))


if __name__ == "__main__":
    cli()

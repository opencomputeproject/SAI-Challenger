#!/usr/bin/python3

import click
from sai import SaiObjType
from sai_npu import SaiNpu

VERSION = '0.1'

exec_params = {
    "server": "localhost",
    "traffic": False,
    "saivs": False,
    "loglevel": "NOTICE"
}


# This is our main entrypoint - the main 'sai' command
@click.group()
def cli():
    pass


# 'get' command
@cli.command()
@click.argument('oid', metavar='<oid>', required=True, type=str)
@click.argument('attrs', metavar='<attr> [<attr_type>]', required=True, type=str, nargs=-1)
def get(oid, attrs):
    """Retrieve SAI object's attributes"""

    click.echo()
    if not oid.startswith("oid:"):
        click.echo("SAI object ID must start with 'oid:' prefix\n")
        return False

    sai = SaiNpu(exec_params)
    for i in range(0, len(attrs), 2):
        if not attrs[i].startswith("SAI_"):
            click.echo("Invalid SAI object's attribute {} provided\n".format(attrs[i]))
            return False

        attr_type = ''
        if i < len(attrs) - 1:
            attr_type = attrs[i + 1]

        status, data = sai.get_by_type(oid, attrs[i], attr_type, False)
        if status != "SAI_STATUS_SUCCESS":
            click.echo(status + '\n')
            return False

        data = data.to_json()
        click.echo("{:<32} {}".format(data[0], data[1]))

    click.echo()


# 'set' command
@cli.command()
def set():
    """Set SAI object's attribute value"""
    click.echo("\nNot implemented!\n")
    return False


# 'create' command
@cli.command()
def create():
    """Create SAI object"""
    click.echo("\nNot implemented!\n")
    return False


# 'remove' command
@cli.command()
def remove():
    """Remove SAI object"""
    click.echo("\nNot implemented!\n")
    return False


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


# 'version' subcommand
@cli.command()
def version():
    """Display version info"""
    click.echo("SAI CLI version {0}".format(VERSION))


if __name__ == "__main__":
    cli()

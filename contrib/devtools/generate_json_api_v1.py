#!/usr/bin/env python3

import re
import subprocess as sp
import sys
import json

re_full = re.compile(r'(?P<name>^.*?$)(?P<desc>.*?)(^Argument.*?$(?P<args>.*?))?(^Result[^\n]*?:\s*$(?P<resl>.*?))?(^Exampl.*?$(?P<exmp>.*))?', re.DOTALL | re.MULTILINE)
re_argline = re.compile(r'^("?)(?P<name>.*?)\1\s+\((?P<type>.*?)\)\s*(?P<desc>.*)$', re.DOTALL)


def get_type(arg_type, full_line):
    if arg_type is None:
        return 'string'

    arg_type = arg_type.lower()
    if 'numeric' in arg_type:
        return 'number'
    if 'bool' in arg_type:
        return 'boolean'
    if 'string' in arg_type:
        return 'string'
    if 'object' in arg_type:
        return 'object'

    raise Exception('Not implemented: ' + arg_type)


def parse_params(args):
    arguments = []
    if args:
        for line in re.split('\s*\d+\.\s+', args, re.DOTALL):
            if not line or not line.strip() or line.strip().startswith('None'):
                continue
            arg_parsed = re_argline.fullmatch(line)
            if arg_parsed is None:
                raise Exception("Unparsable argument: " + line)
            arg_name, arg_type, arg_desc = arg_parsed.group('name', 'type', 'desc')
            if not arg_type:
                raise Exception('Not implemented: ' + arg_type)
            arg_required = 'required' in arg_type or 'optional' not in arg_type
            arg_refined_type = get_type(arg_type, line)
            arg_desc = re.sub('\s+', ' ', arg_desc.strip()) if arg_desc else []
            arguments.append({
                'name': arg_name,
                'type': arg_refined_type,
                'description': arg_desc,
                'is_required': arg_required
            })
    return arguments


def get_api(section_name, command, command_help):

    parsed = re_full.fullmatch(command_help)
    if parsed is None:
        raise Exception('Unable to resolve help format for ' + command)

    name, desc, args, resl, exmp = parsed.group('name', 'desc', 'args', 'resl', 'exmp')

    arguments = parse_params(args)

    cmd_desc = re.sub('\s+', ' ', desc.strip()) if desc else ''
    if exmp and '--skip_examples' not in sys.argv:
        cmd_desc += '\nExamples:\n' + exmp.strip()
    cmd_resl = resl.strip() if resl else None

    ret = {
        'name': command,
        'namespace': section_name,
        'description': cmd_desc,
        'arguments': arguments,
    }
    if cmd_resl is not None:
        ret['returns'] = cmd_resl
    return ret


def write_api():
    if len(sys.argv) < 2:
        print("Missing required argument: <path to CLI tool>", file=sys.stderr)
        sys.exit(1)
    cli_tool = sys.argv[1]
    result = sp.run([cli_tool, "help"], stdout=sp.PIPE, universal_newlines=True)
    commands = result.stdout
    sections = re.split('^==\s*(.*?)\s*==$', commands, flags=re.MULTILINE)
    apis = []
    for section in sections:
        if not section:
            continue
        lines = section.splitlines()
        if len(lines) == 1:
            section_name = lines[0]
            continue
        for command in sorted(lines[1:]):
            if not command:
                continue
            command = command.split(' ')[0]
            result = sp.run([cli_tool, "help", command], stdout=sp.PIPE, universal_newlines=True)
            apis.append(get_api(section_name, command, result.stdout))

    print(json.dumps(apis, indent=4))


if __name__ == '__main__':
    write_api()

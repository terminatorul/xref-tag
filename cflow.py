"""
    SCons tool for `cflow` command: https://www.gnu.org/software/cflow/


    Ex. cflow installation for Ubuntu: `apt install cflow`

    Syntax:
        flow_tree = CFlowTree('cflowtree', [ target, ... ])
        flow_tree = CFlowTree([ target, ... ])
        flow_tree = CFlowTree([ target, ... sources, ... ])

    If omitted, the output file name is the name of the target with the .cflow extension. Additional files are
    created with extensions .reverse.cflow and xref.cflow for the reverse tree and the cflow cross-reference.

    The dependencies list should be a target from your build script. Source dependencies of such targets will
    be traversed and added to the list of input files for `cflow` command.

    Each source suffix will be checked against the suffix list in env['CFLOWSUFFIXES'], and only the matching
    files are processed. You can disable the check by using the string '*' as the first list entry.

    `cflow` uses pre-processed sources (*.i) by default, and if so it requires the 'gcc-cpp' tool for
    injecting the needed gcc options and resulting targets for pre-processed source files.
"""

import sys
import os
import subprocess
import SCons.Script
import source_browse_base as base

""" default name for `cflow` executable command """
cflow_bin = 'cflow'

def collect_source_dependencies(target, source, env):
    """ emitter function for CFlowTree() builder, for listing sources of any target node included in the tags file """

    ext = os.path.splitext(str(target[0]))

    keys_list = env['CFLOWFORMAT'].keys()

    del target[0]

    keys_list.sort()
    keys_list.reverse()
    for k in keys_list:
        target.insert(0,  ''.join([ ext[0], k, ext[1] ]))

    if 'CFLOWCONFIG' in env:
        for tgt in target:
            for config in env.Split(env['CFLOWCONFIG']):
                if os.path.exists(config):
                    env.Depends(tgt, config)

    return base.collect_source_dependencies(target, source, env, 'CFLOWSUFFIXES')
    # source_files = { }

    # for node in source:
    #     if node.is_derived():
    #         # print("Adding derived dependency on " + str(node))
    #         for tgt in target:
    #             env.Depends(tgt, node)

    #             for src in env.FindSourceFiles(tgt):
    #                 src_ext = os.path.splitext(str(src))

    #                 if src_ext[1] in env['CFLOWSUFFIXES'] or len(env['CFLOWSUFFIXES']) and env['CFLOWSUFFIXES'][0] == '*':
    #                     if src_ext[1] == '.c':
    #                         source_files[src_ext[0] + '.i'] = True
    #                     else:
    #                         source_files[src_ext[0] + '.ii'] = True
    #     else:
    #         src_ext = os.path.splitext(str(node))

    #         if src_ext[1] in env['CFLOWSUFFIXES'] or len(env['CFLOWSUFFIXES']) and env['CFLOWSUFFIXES'][0] == '*':
    #             if src_ext[1] == '.c':
    #                 source_files[src_ext[0] + '.i'] = True
    #             else:
    #                 source_files[src_ext[0] + '.ii'] = True

    # return target, [ env.File(src).path for src in source_files.keys() ]

def run_cflow(target, source, env):
    """ action function invoked by the CFlowTree() Builder to run `cflow` command """

    command = env.Split(env['CFLOW']) + env.Split(env['CFLOWFLAGS']) + (env.subst(env.Split(env['CFLOWCPP'])) if 'CFLOWCPP' in env else [ ])

    if len(env.Split(env['CFLOWCPP'])):
        for definition in env.Split(env['CFLOWSDEF']):
            command += env.Split(env['CFLOWSDEFFLAG']) + [ definition ]

        for inc in env.Split(env['CFLOWPATH']):
            command += env.Split(env['CFLOWPATHFLAG']) + [ inc ]

    for sym in env.Split(env['CFLOWSYM']):
        command += env.Split(env['CFLOWSYMFLAG']) + [ sym ]

    keys_list = env['CFLOWFORMAT'].keys()
    keys_list.sort()

    target_index = 0

    for nested_ext in keys_list:
        format_command = command[:]
        format_command += env.Split(env['CFLOWFORMAT'][nested_ext]) + env.Split(env['CFLOWOUTPUTFLAG']) + [ str(target[target_index]) ]
        format_command += [ str(src) for src in source ]

        target_index = target_index + 1

        print(' '.join(base.shell_escape(format_command)))

        cflow_process = subprocess.check_output(format_command, env = env['ENV'])

def exists(env):
    """ Check if `cflow` tool is imported in the environment """
    return env['CFLOW'] if 'CFLOW' in env else None

def show_cflow_generation_message(target, source, env):
    pass

def generate(env, **kw):
    """
        Populate environment with variables for the CFlowTree() builder:

            $CFLOW, $CFLOWOUTPUTFLAG, $CFLOWFLAGS, $CFLOWCONFIG, $CFLOWPATHFLAG, $CFLOWPATH, $CFLOWDEFSUFFIXESa, $CFLOWSDEFFLAG, $CFLOWDEF,
            $CFLOWFORMAT, $CFLOWSYMFLAGS, $CFLOWSYM, $CFLOWSUFFIXES, $CFLOWCPP

        Attach the TagsFile() builder to the environment.
    """

    env.SetDefault\
        (
            CFLOW           = cflow_bin,
            CFLOWOUTPUTFLAG = [ '--output' ],
            CFLOWFLAGS      = [ '--all', '--omit-symbol-name' ],
            CFLOWCONFIG     = [ os.path.join(os.environ['HOME'], '.cflowrc') ],
            CFLOWPATHFLAG   = [ '-I' ],
            CFLOWPATH       = [ ],
            CFLOWDEFFLAG    = [ '-D' ],
            CFLOWDEF        = [ ],
            CFLOWFORMAT     = { '': [ ], '.reverse': [ '--reverse' ], '.xref': [ '--xref' ] },
            CFLOWSYMFLAG    = [ '--symbol' ],
            CFLOWSYM        =
                [
                    '__inline:=inline',
                    '__inline__:=inline',
                    '__gnu_inline__:=inline',
                    '__always_inline__:=inline',
                    '__const__:=const',
                    '__const:=const',
                    '__restrict:=',
                    '__extension__:qualifier',
                    '__attribute__:wrapper',
                    '__asm__:wrapper',
                    '__nonnull:wrapper',
                    '__nonnull__:wrapper',
                    '__wur:wrapper',
                    '__nonnull__:wrapper',
                    '__artificial__:qualifier',
                    '__leaf__:qualifier',
                    '__nothrow__:qualifier',
                    '__artificial__:qualifier',
                    '__pure__:qualifier',
                    '__asm__:qualifier'
                ],
            CFLOWSUFFIXES   =
                [
                    '.c', '.y',
                    '','.c++', '.cc', '.cp', '.cpp', '.cxx', '.h', '.h++', '.hh', '.hp', '.hpp', '.hxx', '.C', '.H', '.tcc'
                ],
            CFLOWCPP        = [ ]
        )

    env['BUILDERS']['CFlowTree'] = env.Builder\
            (
                emitter = collect_source_dependencies,
                action  = SCons.Script.Action(run_cflow, show_cflow_generation_message),
                multi   = True,
                name    = 'CFlowTree',
                suffix  = 'cflow',
                # source_scanner = SCons.Script.CScan
            )


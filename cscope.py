"""
    SCons tool for `cscope` command.

    The CScopeXRef() builder assumes the `cscope` command from http://cscope.sourceforge.net/.

    Ex. cscope installation for Ubuntu: `apt install cscope`

    Syntax:
        CScopeXRef('xreffile', [ target, ... ])
        CScopeXRef([ target, ... ])
        CScopeXRef([ target, ... sources, ... ])

    If omitted, the output cross-reference file name is given in $CSCOPEFILE, default '#cscope.out'. Files for
    two additional indexes will be created by default to speed up searches: '#csope.in.out' and '#cscope.po.out'

    The dependencies are usually other targets from your build script. Source dependencies of such targets will
    be traversed and added to the list of input files for `cscope` command.

    Each source suffix will be checked against the suffix list in env['CSCOPESUFFXIES'], and only the matching
    files are processed. You can disable the check by using the string '*' as the first list entry.

    To guarantee all symbols are visible to the `cscope` command, and listed in the resulting cross-reference file,
    the `cscope` tool should be used together with `gcc-dep`, to have full dependecy information (nested include
    files) generated by gcc / g++ compiler. Otherwise only the source dependencies visible to the SCons internal
    C/C++ scanner will be available to `cscope` command.
"""

from __future__ import print_function

import sys
import os
import subprocess
import SCons.Script
import source_browse_base as base

""" default name for `cscope` executable command """
cscope_bin = 'cscope'

def collect_source_dependencies(target, source, env):
    """ emitter function for CScopeXRef() builder, for listing sources of any target node included in the xref file """

    ext = os.path.splitext(str(env.File(target[0]).path)) if len(target) else ''

    if ext[1] == '.9afe1b0b-baf3-4dde-8c8f-338b120bc882':
        if len(source) and ext[0] == os.path.splitext(str(env.File(source[0]).path))[0]:
            target = [ ]
        else:
            target[0] = ext[0]  # remove automatically added extension

    getList = base.BindCallArguments(base.getList, target, source, env, False)
    getString = base.BindCallArguments(base.getString, target, source, env, None)

    if not len(target):
        target.append(getString('CSCOPEFILE'))

    for flag in getList('CSCOPEQUICKFLAG'):
        if flag in getList('CSCOPEFLAGS'):
            target += [ str(target[0]) + '.in', str(target[0]) + '.po' ]
            break

    if getString('CSCOPENAMEFILE'):
        target.append(getString('CSCOPENAMEFILE'))

        default_namefile = getString('CSCOPEDEFAULTNAMEFILE')

        if getString('CSCOPENAMEFILE') == default_namefile:
            env.SideEffect(default_namefile + '.8ebd1f37-538d-4d1b-a9f7-7fefa88581e4'. target)

    return base.collect_source_dependencies(target, source, env, 'CSCOPESUFFIXES', True)

def run_cscope(target, source, env):
    """ action function invoked by the CScopeXRef() Builder to run `cscope` command """

    getList     = base.BindCallArguments(base.getList,   target, source, env, False)
    getPathList = base.BindCallArguments(base.getPathList, target, source, env, False)
    getString   = base.BindCallArguments(base.getString, target, source, env, None)

    command = getList('CSCOPE') + getList('CSCOPEFLAGS')

    command += getList('CSCOPESTDINFLAGS') + getList('CSCOPEOUTPUTFLAG') + [ str(target[0]) ]

    namefile = None

    if 'CSCOPENAMEFILE' in env:
        namefile = open(str(env.File(getString('CSCOPENAMEFILE'))), 'w')

        nameFileFlags = getList('CSCOPENAMEFILEFLAGS')

        for arg in command:
            if arg in nameFileFlags:
                namefile.write(arg)
                namefile.write('\n')

    for incdir in getPathList('CSCOPEPATH') + getPathList('CSCOPESYSPATH'):
        command += getList('CSCOPEINCFLAG') + [ incdir ]

        if namefile is not None:
            for arg in getList('CSCOPEINCFLAG'):
                namefile.write(arg)
                namefile.write(' ')

            if incdir.find(' ') >= 0:
                incdir = '"' + incdir.replace('\\', '\\\\').replace('"', '\\"') + '"'

            namefile.write(incdir)
            namefile.write('\n')

    try:
        print(" ".join(base.shell_escape(command)))

        cscope_process = subprocess.Popen(command, stdin = subprocess.PIPE, env = env['ENV'])

        source.sort()
        for file in source:
            file_str = str(file)

            if file_str.find(' ') >= 0:
                file_str = '"' + file_str.replace('\\', '\\\\').replace('"', '\\"') + '"'

            # print("Generating xrefs for source file " + file_str)
            if namefile is not None:
                namefile.write(file_str + '\n')

            cscope_process.stdin.write(file_str + '\n')

        cscope_process.stdin.close()

        if cscope_process.wait():
            sys.stderr.write("cscope command exited with code: " + str(cscope_process.returncode) + '\n')
            return cscope_process.returncode
    finally:
        if namefile is not None:
            namefile.close()

def process_source_and_target(target, source, env):
    """ emitter function for CScopeDirXRef() builder, for listing sources of any target node included in the xref file """

    ext = os.path.splitext(str(env.File(target[0]).path)) if len(target) else ''

    if ext[1] == '.8ebd1f37-538d-4d1b-a9f7-7fefa88581e4':
        if len(source) and ext[0] == os.path.splitext(str(env.File(source[0]).path))[0]:
            target = [ ]
        else:
            target[0] = ext[0]  # remove automatically added extension

    getList = base.BindCallArguments(base.getList, target, source, env, False)
    getString = base.BindCallArguments(base.getString, target, source, env, None)

    if not target:
        target.append(getString('CSCOPEFILE'))

    for flag in getList('CSCOPEQUICKFLAG'):
        if flag in getList('CSCOPEFLAGS'):
            target += [ str(target[0]) + '.in', str(target[0]) + '.po' ]
            break

    default_namefile = getString('CSCOPEDEFAULTNAMEFILE')

    if default_namefile:
        env.SideEffect(default_namefile + '.8ebd1f37-538d-4d1b-a9f7-7fefa88581e4', target)

    # if env.Dir('.').srcnode() not in source:
    #     source = [ env.Dir('.').srcnode() ] + source

    return env.AlwaysBuild(target), source

def run_cscope_on_dirs(target, source, env):
    """ action function invoked by the CScopeDirXRef() Builder to run `cscope` command """

    getList     = base.BindCallArguments(base.getList,     target, source, env, False)
    getPathList = base.BindCallArguments(base.getPathList, target, source, env, False)
    getString   = base.BindCallArguments(base.getString,   target, source, env, None)

    command = getList('CSCOPE') + getList('CSCOPEFLAGS') + getList('CSCOPEOUTPUTFLAG') + [ str(target[0]) ]

    for incdir in getPathList('CSCOPEPATH') + getPathList('CSCOPESYSPATH'):
        command += getList('CSCOPEINCFLAG') + [ incdir ]

    for srcdir in source:
        command += getList('CSCOPESOURCEDIRFLAG') + [ str(srcdir) ]

    default_namefile = getString('CSCOPEDEFAULTNAMEFILE')

    if os.path.exists(default_namefile):
        os.rename(default_namefile, default_namefile + '.8ebd1f37-538d-4d1b-a9f7-7fefa88581e4')

    try:
        print(' '.join(base.shell_escape(command)))

        return subprocess.Popen(command, env = env['ENV']).wait()
    finally:
        if os.path.exists(default_namefile):
            os.rename(default_namefile + '.8ebd1f37-538d-4d1b-a9f7-7fefa88581e4', default_namefile)

def exists(env):
    """ Check if `cscope` command is present """
    return env['CSCOPE'] if 'CSCOPE' in env else None

def show_refs_generation_message(target, source, env):
    pass

def generate(env, **kw):
    """
        Populate environment with variables for the CScopeXRef() builder:
            $CSCOPE, $CSCOPEFILE, $CSCOPEFLAGS, $CSCOPEPATH, $CSCOPEINCFLAG,
            $CSCOPESUFFIXES, $CSCOPESTDINFLAGS, $CSCOPEOUTPUTFLAG,
            $CSCOPESOURCESUFFIXES, $CSCOPERECURSIVEFLAG, $CSCOPESOURCEDIRFLAG,
            $CSCOPEDEFAULTNAMEFILE

        Attach the CScopeXRef() and CScopeDirXRef() builders to the environment.
    """

    env.SetDefault\
        (
            CSCOPE              = cscope_bin,
            CSCOPEQUICKFLAG     = [ '-q' ],
            CSCOPEFLAGS         = [ '-b', '-q', '-k' ],
            CSCOPEINCFLAG       = [ '-I' ],
            CSCOPEPATH          = lambda target, source, env, for_signature: env['CPPPATH'],
            CSCOPESYSPATH       = [ ],
            CSCOPESTDINFLAGS    = [ '-i', '-' ],
            CSCOPEOUTPUTFLAG    = [ '-f' ],
            CSCOPEFILE          = '#cscope.out',
            CSCOPENAMEFILE      = '#cscope.files',
            CSCOPENAMEFILEFLAGS = [ '-I', '-c', '-k', '-p', '-q', '-T' ],
            CSCOPESUFFIXES      =
                [
                    '',
                    '.c', '.y', '.l',
                    '.i', '.c++', '.cc', '.cp', '.cpp', '.cxx', '.C',
                    '.h', '.h++', '.hh', '.hp', '.hpp', '.hxx', '.H', '.tcc',
                ],
            CSCOPESOURCESUFFIXES  =
                [
                    '.c', '.y', '.l', '.i', '.c++', '.cc', '.cp', 'cpp', '.C'
                ],
            CSCOPERECURSIVEFLAG   = [ '-R' ],
            CSCOPESOURCEDIRFLAG   = [ '-s' ],
            CSCOPEDEFAULTNAMEFILE = 'cscope.files'
        )

    env['BUILDERS']['CScopeXRef'] = env.Builder\
            (
                emitter = collect_source_dependencies,
                action  = SCons.Script.Action(run_cscope, show_refs_generation_message),
                multi   = True,
                name    = 'CScopeXRef',
                suffix  = '9afe1b0b-baf3-4dde-8c8f-338b120bc882',
                # source_scanner = SCons.Script.CScan
            )

    env['BUILDERS']['CScopeDirXRef'] = env.Builder\
            (
                emitter         = process_source_and_target,
                action          = SCons.Script.Action(run_cscope_on_dirs, show_refs_generation_message),
                multi           = True,
                name            = 'CScopeDirXRef',
                suffix          = '8ebd1f37-538d-4d1b-a9f7-7fefa88581e4',
                source_factory  = SCons.Script.Dir
            )


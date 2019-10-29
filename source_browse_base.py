"""
    Base python module for SCons source code browsing Tools:

        - ctags
        - gtags
        - cscope
        - cflow

    Utility functions for SCons tools
"""

import os
import re
import SCons.Script

def getList(target, source, env, for_siganture, var):
    return env.Split(env[var](target, source, env, False) if callable(env[var]) else env[var]) if var in env else [ ]

def getString(target, source, env, conv, var):
    return env.subst(env[var](target, source, env, False) if callable(env[var]) else env[var], False, target, source) if var in env else ''

class BindCallArguments:
    """ Creates a path_function for Scanner's, given a callable returned by FindPathDirs() """
    def __init__(self, baseObject, *arglist):
        self.baseObject = baseObject
        self.arglist = arglist

    def __call__(self, *args, **kw):
        return self.baseObject(*(self.arglist + args), **kw)

def collect_source_dependencies(target, source, env, suffix_list_var, readlink = False):
    """ base emitter function for the source tagging builders, for listing sources of any target node included in the tags file """

    source_files = { }

    getListFunc = BindCallArguments(getList, target, source, env, False)
    getStringFunc = BindCallArguments(getString, target, source, env, None)

    suffix_list = getListFunc(suffix_list_var) if suffix_list_var else [ ]

    for node in source:
        if node.is_derived():
            # print("Adding derived dependency on " + str(node))
            for tgt in target:
                env.Depends(tgt, node)
        else:
            if node.get_suffix() in getListFunc('CPPSUFFIXES'):
                for dep in SCons.Script.CScanner(node, env, BindCallArguments(SCons.Script.FindPathDirs('CPPPATH'), env)):
                    source_files[str(dep)] = True
            source_files[str(node)] = True

        nodeWalker = SCons.Node.Walker(node)

        child = nodeWalker.get_next()

        while child:
            if not child.is_derived():
                file_name = str(child)

                if readlink and os.path.islink(file_name):
                    if os.path.isabs(file_name):
                        file_name = os.path.realpath(file_name)
                    else:
                        file_name = os.path.relpath(os.path.realpath(file_name))

                ext = os.path.splitext(file_name)[1]

                if not suffix_list_var or ext in suffix_list or len(suffix_list) and suffix_list[0] == '*':
                    source_files[file_name] = True

            child = nodeWalker.get_next()

    for cmd in [ 'CC', 'CXX', 'AR', 'RANLIB', 'AS', 'LINK', 'SHCC', 'SHCXX', 'SHLINK' ]:
        bin_path = env.WhereIs(env[cmd]) if cmd in env else None

        if bin_path is not None and bin_path in source_files:
            del source_files[str(bin_path)]

    return target, source_files.keys()

shell_metachars_re = re.compile('[' + re.escape("|&;<>()$`\\\"' \t\r\n!*?[#~%]") + ']')

def shell_escape(args):
    return [ "'" + arg.replace("'", "'\\''") + "'" if not arg or re.search(shell_metachars_re, arg) else arg for arg in args ]


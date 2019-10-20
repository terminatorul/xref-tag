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

class FindPathProxy:
    """ Creates a path_function for Scanner's, given a callable returned by FindPathDirs() """
    def __init__(self, baseObject, arg):
        self.baseObject = baseObject
        self.arg = arg

    def __call__(self, *args, **kw):
        return self.baseObject(self.arg, *args, **kw)

def collect_source_dependencies(target, source, env, suffix_list_var):
    """ base emitter function for the source tagging builders, for listing sources of any target node included in the tags file """

    source_files = { }

    for node in source:
        if node.is_derived():
            # print("Adding derived dependency on " + str(node))
            for tgt in target:
                env.Depends(tgt, node)
        else:
            if node.get_suffix() in env['CPPSUFFIXES']:
                for dep in SCons.Script.CScanner(node, env, FindPathProxy(SCons.Script.FindPathDirs('CPPPATH'), env)):
                    source_files[str(dep)] = True
            source_files[str(node)] = True

        nodeWalker = SCons.Node.Walker(node)

        child = nodeWalker.get_next()

        while child:
            if not child.is_derived():
                if not suffix_list_var or child.get_suffix() in env[suffix_list_var] or len(env[suffix_list_var]) and env[suffix_list_var][0] == '*':
                    source_files[str(child)] = True

            child = nodeWalker.get_next()

    for cmd in [ 'CC', 'CXX', 'AR', 'RANLIB', 'AS', 'LINK', 'SHCC', 'SHCXX', 'SHLINK' ]:
        bin_path = env.WhereIs(env[cmd]) if cmd in env else None

        if bin_path is not None and bin_path in source_files:
            del source_files[str(bin_path)]

    return target, source_files.keys()

shell_metachars_re = re.compile('[' + re.escape("|&;<>()$`\\\"' \t\r\n!*?[#~%]") + ']')

def shell_escape(args):
    return [ "'" + arg.replace("'", "'\\''") + "'" if not arg or re.search(shell_metachars_re, arg) else arg for arg in args ]


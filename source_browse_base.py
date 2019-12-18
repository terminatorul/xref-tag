"""
    Base python module for SCons source code browsing Tools:

        - ctags
        - gtags
        - cscope
        - cflow

    Utility functions for SCons tools
"""
import sys
import os
import re
import SCons.Script

from generated_list import generated_list
from TreeWalker import TreeWalker

class BindCallArguments:
    """ Creates a path_function for Scanner's, given a callable returned by FindPathDirs() """
    def __init__(self, baseObject, *arglist):
        self.baseObject = baseObject
        self.arglist = arglist

    def __call__(self, *args, **kw):
        return self.baseObject(*(self.arglist + args), **kw)

def getList(target, source, env, for_signature, var):
    return env.Split(env[var](target, source, env, False) if callable(env[var]) else env[var]) if var in env else [ ]

def getPathList(target, source, env, for_signature, var):
    return [ str(env.Dir(path)) for path in getList(target, source, env, for_signature, var) ]

def getString(target, source, env, conv, var):
    return env.subst(env[var](target, source, env, False) if callable(env[var]) else env[var], True, target, source, conv) if var in env else ''

def getPath(target, source, env, conv, var):
    return str(env.Dir(getString(target, source, env, conv, var)))

def getBool(target, source, env, conv, var):
    strVal = getString(target, source, env, conv, var)

    if isinstance(strVal, list):
        return not not strVal

    if strVal == '' or strVal == str(False) or strVal == str(False).lower() \
                or \
            strVal == str(None) or strVal == str(None).lower():
        return False

    return not not int(strVal)

def make_rel_path(path):
    """
        translate path if needed to turn a plain basename into a path relative to the current directory,
        e.g. translate 'cscope.exe' to './cscope.exe'

        if given path already includes a directory separator it is returned unchanged
    """
    if os.sep not in path and (not sys.platform.startswith('win') or '/' not in path):
        return os.path.join(os.curdir, path)

    return path

def search_executable(cmd_basename, dirname, top_dir, pathext, env):
    """
        check if cmd is found in dirname/ or one of the repository directories for dirname/, with any
        of the suffixes in pathext.

        Return tuple (isFound, isFoundInLocalDir, foundPathName)
    """

    for ext in pathext:
        if os.path.isfile(os.path.join(dirname, cmd_basename + ext)):
            return True, True, os.path.join(dirname, cmd_basename + ext)

    if not os.path.isabs(dirname) or dirname.startswith(top_dir):
        subdir = os.path.relpath(dirname, top_dir) if os.path.isabs(dirname) else dirname

        for repo in env.Dir(subdir).getRepositories():
            repo_dir = repo.Dir(subdir)

            if os.path.isdir(repo_dir):
                for ext in pathext:
                    if os.path.isfile(os.path.join(repo_dir, cmd_basename + ext)):
                        return True, False, os.path.join(dirname, cmd_basename + ext)

    return False, False, None

def translate_path_executable(cmd, cwd, new_cwd, env):
    """
        Translate command `cmd` so it can be run from directory `new_cwd`, and it will load the same
        executable as `cmd` when run from `cwd`.

        Translation takes into account searching the directories on PATH if `cmd` is a basename only.

        If PATH includes relative directories and `cmd` is found in one of them, `cmd` will be translated
        to full path, so it can still be found from `new_cwd`, unless `new_cwd` is the same directory as
        `cwd`.

        All searches will take into account the equivalent directories from repositories, if any. This way
        PATH can include a directory of scripts from the current project, and they will be found even when
        directory is present only in repository.

        To only search for a command on PATH and in repositories (if applicable), pass the same directory
        for `cwd` and `new_cwd` so other translations will not occur.
    """

    top_dir = str(env.Dir('#').srcnode().abspath)
    dirname, cmd_basename = os.path.split(cmd)

    if sys.platform.startswith('win'):
        pathext = env['ENV']['PATHEXT'].split(os.pathsep) if 'ENV' in env and 'PATHEXT' in env['ENV'] \
                else [ '.COM', '.EXE', '.BAT', '.CMD' ]
    else:
        pathext = [ '' ]

    if os.path.isabs(dirname):
        isFound, isLocal, path = search_executable(cmd_basename, dirname, top_dir, pathext, env)

        if isFound and not isLocal:
            return path

        return cmd

    if os.sep in cmd or sys.platform.startswith('win') and '/' in cmd:
        isFound, isLocal, path = search_executable(cmd_basename, dirname, top_dir, pathext, env)

        if isFound and not isLocal:
            return make_rel_path(os.path.relpath(path, new_cwd))

        return make_rel_path(os.path.relpath(os.path.join(cwd, cmd), new_cwd))

    path = env['ENV']['PATH'].split(os.pathsep) if 'ENV' in env and 'PATH' in env['ENV'] else [ ]

    if sys.platform.startswith('win'):
        path.insert(0, '')

    found_in_new_dir = False
    same_dir = os.path.realpath(cwd) == os.path.realpath(new_cwd)

    for directory in path:
        if os.path.isabs(directory):
            isFound, isLocal, path = search_executable(cmd_basename, directory, top_dir, pathext, env)

            if isFound:
                if isLocal:
                    if found_in_new_dir:
                        return path
                    else:
                        return cmd
                else:
                    return path
        else:
            isFound, isLocal, path = \
                search_executable(cmd_basename, os.path.join(cwd, directory), top_dir, pathext, env)

            if isFound:
                if isLocal:
                    if found_in_new_dir:
                        return path
                    else:
                        if same_dir:
                            return cmd
                        else:
                            return path
                else:
                    return path
            else:
                found_in_new_dir, isLocal, path = \
                    search_executable(cmd_basename, os.path.join(new_cwd, directory), top_dir, pathext, env)

    # command not found on path
    return cmd

def translate_relative_path(path, old_cwd, new_cwd):
    """ Translate `path` relative to `old_cwd` into the equivalent path relative to `new_cwd` """
    if os.path.isabs(path):
        return path
    else:
        return os.path.relpath(os.path.join(old_cwd, path), new_cwd)

def translate_include_path(env, path_list, variant_dir, target_dir, include_variant_dir):
    """
        Translate path_list directories relative to variant_dir, to make them relative to target_dir.
        Corresponding linked (source) directories for variant_dir are included in the resulting list.
        Corresponding repository directories are included in the resulting list.
        Directories under the variant_dir will be excluded if include_variant_dir is False
    """

    variant_dir = env.Dir(variant_dir)
    local_dir   = env.Dir(variant_dir).srcnode()
    target_dir  = env.Dir(target_dir)

    translated_path = [ ]

    for user_incdir in path_list:
        basedir_list = [ local_dir ]

        if include_variant_dir and variant_dir != local_dir and not os.path.isabs(user_incdir):
            basedir_list.append(variant_dir)

        for basedir in basedir_list:
            incdir_name = basedir.Dir(user_incdir)

            for incdir in \
                    [ incdir_name ] + [ repo.Dir(incdir_name) for repo in incdir_name.getRepositories() ]:
                translated_path.append(translate_relative_path(str(incdir), '.', str(target_dir)))

    return translated_path

def collect_source_dependencies(keepVariantDir, target, source, env, suffix_list_var, readlink = False):
    """ base emitter function for the source tagging builders, for listing sources of any target node included in the tags file """

    source_files = { }

    getListFunc = BindCallArguments(getList, target, source, env, False)
    getStringFunc = BindCallArguments(getString, target, source, env, None)

    suffix_list = getListFunc(suffix_list_var) if suffix_list_var else [ ]

    if not 'GCCDEP_INJECTED' in env or not env['GCCDEP_INJECTED']:
        raise SCons.Errors.UserError("Tool('xref-tag.gcc-dep') is needed for building " + str(target[0]))

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

        nodeWalker = TreeWalker(node)

        child, parent = nodeWalker.next_child()

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

            child, parent = nodeWalker.next_child()

    for cmd in [ 'CC', 'CXX', 'AR', 'RANLIB', 'AS', 'LINK', 'SHCC', 'SHCXX', 'SHLINK' ]:
        bin_path = env.WhereIs(env[cmd]) if cmd in env else None

        if bin_path is not None:
            if bin_path in source_files:
                del source_files[str(bin_path)]

            bin_path = os.path.realpath(str(bin_path))

            if bin_path in source_files:
                del source_files[bin_path]


    if keepVariantDir:
        source_list = source_files.keys()
    else:
        source_list = [ env.File(src).srcnode() for src in source_files ]

    return target, source_list

shell_metachars_re = re.compile('[' + re.escape("|&;<>()$`\\\"' \t\r\n!*?[#~%]") + ']')

def shell_escape(args):
    return [ "'" + arg.replace("'", "'\\''") + "'" if not arg or re.search(shell_metachars_re, arg) else arg for arg in args ]


def match_ixes(node, prefix, suffix):
    basename = os.path.split(node.get_path())[1]

    return basename.startswith(prefix) and node.get_suffix() == suffix

def is_object_file(node, obj_ixes):
    """
        check the node is derived (built) and the file name matches convention for static or shared
        object file
    """
    if node.is_derived():
        basename = os.path.split(node.get_path())[1]

        return \
            basename.startswith(obj_ixes[0]) and node.get_suffix() == obj_ixes[1] \
                or \
            basename.startswith(obj_ixes[2]) and node.get_suffix() == obj_ixes[3]

    return False

def has_flags(flag_list, sublist):
    for flag in sublist:
            if flag not in flag_list:
                return False

    return True

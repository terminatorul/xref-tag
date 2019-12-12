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

class BindCallArguments:
    """ Creates a path_function for Scanner's, given a callable returned by FindPathDirs() """
    def __init__(self, baseObject, *arglist):
        self.baseObject = baseObject
        self.arglist = arglist

    def __call__(self, *args, **kw):
        return self.baseObject(*(self.arglist + args), **kw)

class generated_list(list):
    """
        List class populated with elements using the given generator.

        The generator will be invoked whenever the list is iterated, searched or counted.

        Because of this property the class can be used as an optimization to wrap a generator as a
        'built-in list', in specific cases when you need both:
            - an object that successfully type-checks as a build-in list, ex. isinstance(obj, list)
            - you need to iterate only one element at a time, so the expanded list is never needed

        A simple use case is when the list is used only once or so, and you want to delay evaluation of
        the generator until that time.

        Any direct element access (lst[i]), list slices with negative or reverse-order bounds, list
        concatenation or multiplication and any list modification will internally populate a python
        built-in list with values return by the generator. Afterwards the object behaves like a python
        built-in list, and the generator is forgotten.
    """

    def __init__(self, gen_fn, *gen_args):
        super(generated_list, self).__init__()
        self.gen_fn = gen_fn
        self.gen_args = gen_args
        self.nonzero = None

    def Expand(self):
        """
            Request populating the internal python built-in list with the elements returned by the
            generator. Use this in advance if you want to avoid repeated calls of the generator and use
            the extra memory for a real list instead. The generator function will be forgotten after the
            call.
        """
        if self.gen_fn:
            super(generated_list, self).extend([ x for x in self.gen_fn(*self.gen_args) ])
            self.gen_fn = None
            self.gen_args = None

    def _sequence_comparation(self, other, cmp_fn):
        if self.gen_fn:
            other_it = None
            other_x = None
            try:
                other_it = other.__iter__()
            except AttributeError:
                Expand()
                return cmp_fn(self, other)

            for x in self.gen_fn(*self.gen_args):
                try:
                    other_x = other_it.next()
                except StopIteration:
                    return cmp_fn(1, 0)

                result = cmp_fn(x, other_x)

                if result:
                    return result

            try:
                other_x = other_it.next()
                return cmp_fn(0, 1)
            except StopIteration:
                return cmp_fn(0, 0)
        else:
            return cmp_fn(self, other)

    def __cmp__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: -1 if l < r else (1 if l > r else 0))
        else:
            if hasattr(list, '__cmp__'):
                return super(self, '__cmp__')(other)
            else:
                if super(self, '__lt__')(other):
                    return -1
                else:
                    if super(self, '__gt__')(other):
                        return 1
                    else:
                        return 0

    def __lt__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: l < r)
        else:
            if hasattr(list, '__lt__'):
                return super(generated_list, self).__lt__(other)
            else:
                return super(generated_list, self).__cmp__(other) < 0

    def __le__(self, other):
        if self.gen_fn:
            return self.__cmp__(other) <= 0
        else:
            if hasattr(list, '__le__'):
                return super(generated_list, self).__le__(other)
            else:
                return super(generated_list, self).__cmp__(other) <= 0

    def __eq__(self, other):
        if self.gen_fn:
            return not self._sequence_comparation(other, lambda l, r: not l == r)
        else:
            if hasattr(list, '__eq__'):
                return super(generated_list, self).__eq__(other)
            else:
                return not super(generated_list, self).__cmp__(other)

    def __ne__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: l != r)
        else:
            if hasattr(list, '__ne__'):
                return super(generated_list, self).__ne__(other)
            else:
                return not not super(generated_list, self).__cmp__(other)

    def __gt__(self, other):
        if self.gen_fn:
            return self._sequence_comparation(other, lambda l, r: l > r)
        else:
            if hasattr(list, '__gt__'):
                return super(generated_list, self).__gt__(other)
            else:
                return super(generated_list, self).__cmp__(other) > 0

    def __ge__(self, other):
        if self.gen_fn:
            return self.__cmp__(other) >= 0
        else:
            if hasattr(list, '__ge__'):
                return super(generated_list, self).__ge__(other)
            else:
                return super(generated_list, self).__cmp__(other) >= 0

    def __repr__(self):
        if self.gen_fn:
            return \
                "source_browse_base.generated_list(" \
                    + \
                ', '.join([ repr(x) for x in [ self.gen_fn ] + list(self.gen_args) ]) \
                    + \
                ')'
        else:
            return super(generated_list, self).__repr__()

    def __str__(self):
        if self.gen_fn:
            return '[' + ', '.join([ str(x) for x in self.gen_fn(*self.gen_args) ]) + ']'
        else:
            return super(generator_list, self).__str__()

    def __nonzero__(self):
        if self.gen_fn:
            if self.nonzero is None:
                for x in self.gen_fn(*self.gen_args):
                    self.nonzero = True
                    break

                if not self.nonzero:
                    self.nonzero = False

            return self.nonzero
        else:
            if hasattr(list, '__nonzero__'):
                return super(generated_list, self).__nonzero__()
            else:
                return not not super(generated_list, self).__len__()

    def index(self, val, min_index = None, max_index = None):
        if self.gen_fn and (min_index is None or min_index >= 0) and (max_index is None or max_index >= min_index):
            if min_index is None:
                min_index = 0

            idx = 0
            for x in self.gen_fn(*self.gen_args):
                if idx < min_index:
                    idx += 1
                    continue
                else:
                    if max_index is not None and idx > max_index:
                        break

                if val == x:
                    return idx

                idx += 1

            return -1
        else:
            return super(generated_list, self).index(val)

    def count(self, val):
        if self.gen_fn:
            count = 0

            for x in self.gen_fn(*self.gen_args):
                if val == x:
                    count += 1

            return count
        else:
            return super(generated_list, self).count(val)

    def __len__(self):
        if self.gen_fn:
            length = 0

            for x in self.gen_fn(*self.gen_args):
                length += 1

            return length
        else:
            return super(generated_list, self).__len__()

    def __getitem__(self, pos):
        if \
                self.gen_fn \
                    and \
                isinstance(pos, slice) \
                    and \
                (pos.start is None or pos.start >= 0) \
                    and \
                (pos.stop is None or pos.stop >= pos.start):
            start  = pos.start
            step   = pos.step
            stop   = pos.stop
            idx    = 0
            result = [ ]

            if start is None:
                start = 0

            if step is None or step == 0:
                step = 1

            else:
                if step < 0:
                    step = -step

            for x in self.gen_fn(*self.gen_args):
                if idx < start:
                    idx += 1
                    continue

                if idx > stop:
                    break

                if (idx - start) % step == 0:
                    result.append(x)

                idx += 1

            return result
        else:
            self.Expand()
            return super(generated_list, self).__getitem__(pos)

    def __setitem__(self, pos, val):
        self.Expand()
        return super(generated_list, self).__setitem__(pos, val)

    def __delitem__(self, pos):
        self.Expand()
        return super(generated_lsit, self).__delitem__(pos)

    def __iter__(self):
        if self.gen_fn:
            return self.gen_fn(*self.gen_args)
        else:
            return super(generated_list, self).__iter__()

    def __reversed__(self):
        self.Expand()
        return super(generated_list, self).__reversed__(self)

    def __contains__(self, val):
        if self.gen_fn:
            return self.index(val) >= 0
        else:
            super(generated_list, self).__contains__(val)

    def __getslice__(self, start_pos, end_pos):
        if self.gen_fn and (start_pos is None or start_pos >= 0) and (end_pos is None or end_pos >= 0):
            idx = 0
            result = [ ]

            if start_pos is None:
                start_pos = 0

            for x in self.gen_fn(*self.gen_args):
                if idx < start_pos:
                    idx += 1
                    continue

                if end_pos is not None and idx > end_pos:
                    break;

                result.append(x)
                idx += 1

            if end_pos is not None and idx <= end_pos:
                raise IndexError("List index out of range")

            return result
        else:
            self.Expand()
            return super(generated_list, self).__getslice__(start_pos, end_pos)

    def __setslice__(self, start_pos, end_pos, val):
        self.Expand()
        return super(generated_list, self).__setslice__(start_pos, end_pos, val)

    def __delslice__(self, start_pos, end_pos):
        self.Expand()
        return super(generated_list, self).__delslice__(start_pos, end_pos)

    def __add__(self, other):
        self.Expand()
        return super(generated_list, self).__add__(other)

    def __radd__(self, other):
        self.Expand()
        return super(generated_list, self).__radd__(other)

    def __iadd__(self, other):
        self.Expand()
        return super(generated_list, self).__iadd__(other)

    def __mul__(self, other):
        self.Expand()
        return super(generated_list, self).__mul__(other)

    def __rmul__(self, other):
        self.Expand()
        return super(generated_list, self).__rmul__(other)

    def __imul__(self, other):
        self.Expand()
        return super(generated_list, self).__imul__(other)

    def append(self, val):
        self.Expand()
        return super(generated_list, self).append(val)

    def extend(self, val):
        self.Expand()
        return super(generated_list, self).extend(val)

    def insert(self, pos, val):
        self.Expand()
        return super(generated_list, self).insert(pos, val)

    def pop(self, pos = None):
        self.Expand()

        if pos is None:
            return super(generated_list.self).pop()
        else:
            return super(generated_list.self).pop(pos)

    def remove(self, val):
        self.Expand()
        super(generated_list, self).remove(val)

    def reverse(self):
        self.Expand()
        super(generated_list, self).reverse()

    def sort(self, comp = None, key = None, reverse = False):
        self.Expand()
        if reverse == False:
            if key is None:
                if comp is None:
                    super(generated_list, self).sort()
                else:
                    super(generated_list, self).sort(comp)
            else:
                super(generated_list, self).sort(comp, key)
        else:
            super(generated_list, self).sort(comp, key, reverse)

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


def test_get_generated_list(env, start_pos = 10, upper_bound = 20):
    def print_generator(start, stop):
        for val in range(start, stop):
                print("Generating value " + str(val))
                yield "val_" + str(val)

    return generated_list(print_generator, start_pos, upper_bound)

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

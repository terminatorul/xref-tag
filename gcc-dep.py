"""
    Automatically use gcc / g++ compilers to generate make dependencyy rules for the #include
    files during compilation.

    The generated rules are loaded and depndencies found are added to the corresponding object
    file dependencies.

    make dependency rules are regenerated every time the compiler is invoked for any source
    files in the current environment.

    However this means that newly generated dependencies will only be loaded the next time
    the SConscript file is loaded (next time `scons` runs).

    Requires 'gcc' or 'g++' tools in the current environment, as the options used are
    specific to the GNU compilers.
"""

import os
import re
import errno

import SCons.Script
import SCons.Util

from SCons.Builder import DictEmitter, CompositeBuilder
from SCons.Builder import ListEmitter
from SCons.Action  import ListAction

import source_browse_base as base

def logical_lines(physical_lines, joiner = ''.join):
    logical_line = [ ]

    for line in physical_lines:
        stripped = line.rstrip()
        if stripped.endswith('\\'):
            # a line which continues w/the next physical line
            logical_line.append(stripped[:-1])
        else:
            # a line which does not continue, end of logical line
            logical_line.append(line)
            yield joiner(logical_line)
            logical_line = [ ]

    if logical_line:
        # end of sequence implies end of last logical line
        yield joiner(logical_line)

def XRefParseDepends(self, filename, must_exist = None, only_one = 0, existing_only = False):
    """
        Similar to the SCons environment ParseDepends() method, with the following changes:
            - filenames with spaces and tabs are properly parsed, as long as file names do not end with
              the escape character '\\', which can trigger errors.
            - a target filename with colons is properly parsed
            - provide an option to only add dependencies that exist in the file system, so if user deletes
              or moves a header, the build can still proceed as usual
    """
    filename = self.subst(filename)

    try:
        with open(filename, 'r') as fp:
            lines = [ line for line in logical_lines(fp, '\\\n'.join) ]
    except IOError:
        if must_exist:
            raise
        return

    lines = [ l for l in lines if l[0] != '#' ]

    tdlist = [ ]

    for line in lines:
        try:
            target, depends = re.split(':(?:(?:\s+)|(?:\\\\\n\s+)|$)+', line, 1)
        except (AttributeError, ValueError):
            # Throws AttributeError if line isn't a string.  Can throw
            # ValueError if line doesn't split into two or more elements.
            pass
        else:
            target_list = re.split('(?:(?:(?<!\\\\)\s)|(?:\s\\\\\n\s*)|(?:\\\\\n\s+))+', target)
            source_list = re.split('(?:(?:(?<!\\\\)\s)|(?:\s\\\\\n\s*)|(?:\\\\\n\s+))+', depends)

            targets = [ ]
            sources = set()

            unescape = lambda match: '\\' * ((len(match.group(0)) - 2)/2) + match.group(0)[-1]

            for tgt in target_list:
                if tgt:
                    tgt = re.sub('\\\\\n', '', tgt)
                    targets.append(re.sub('\\\\*\\\\\\s', unescape, tgt))

            build_dir = self.Dir('#').abspath

            for src in source_list:
                if src:
                    src = re.sub('\\\\\n', '', src)
                    src = re.sub('\\\\*\\\\\\s', unescape, src)

                    if not existing_only or (os.path.isfile(src) if os.path.isabs(src) \
                            else os.path.isfile(os.path.join(build_dir, src))):
                        sources.add(src)

            tdlist.append((targets, list(sources)))

    if only_one:
        targets = [ ]

        for td in tdlist:
            targets.extend(td[0])

        if len(targets) > 1:
            raise SCons.Errors.UserError\
                    (
                        "More than one dependency target found in `%s':  %s" % (filename, targets)
                    )

    else:
        for target, depends in tdlist:
            self.Depends(target, depends)

def gcc_dep_emitter(target, source, env):
    """
        emitter function for SCons Builders, injected into the existing Object / SharedObject
        builders in the environment, to include and load the new dependency file with the
        object
    """
    getBool     = base.BindCallArguments(base.getBool,   target, source, env, lambda x: x)
    getString   = base.BindCallArguments(base.getString, target, source, env, None)
    getList     = base.BindCallArguments(base.getList,   target, source, env, False)

    if len(target):
        ext = os.path.splitext(str(source[0]))[1]

        is_cc  = ext in getList('GCCDEP_CSUFFIXES')
        is_cxx = ext in getList('GCCDEP_CXXSUFFIXES')

        is_static_obj = base.match_ixes(target[0], getString('GCCDEP_OBJPREFIX'),   getString('GCCDEP_OBJSUFFIX'))
        is_shared_obj = base.match_ixes(target[0], getString('GCCDEP_SHOBJPREFIX'), getString('GCCDEP_SHOBJSUFFIX'))

        if (is_cc or is_cxx) and (is_static_obj or is_shared_obj):
            if is_cc:
                is_gnu_compiler = getBool('GCCDEP_CHECK_USING_GCC' if is_static_obj else 'GCCDEP_CHECK_USING_SH_GCC')
                has_makedep_flags = ('GCCDEP_MAKEDEP_CFLAGS' in env and env['GCCDEP_MAKEDEP_CFLAGS'])
            else:
                is_gnu_compiler = getBool('GCCDEP_CHECK_USING_GXX' if is_static_obj else 'GCCDEP_CHECK_USING_SH_GXX')
                has_makedep_flags = ('GCCDEP_MAKEDEP_CXXFLAGS' in env and env['GCCDEP_MAKEDEP_CXXFLAGS'])


            if is_gnu_compiler:
                if not has_makedep_flags:
                    if is_cc:
                        env['GCCDEP_MAKEDEP_CFLAGS'] = env['GCCDEP_CFLAGS']
                    else:
                        env['GCCDEP_MAKEDEP_CXXFLAGS'] = env['GCCDEP_CXXFLAGS']

                if callable(env['GCCDEP_FILENAME']):
                    # make explicit call, to work around the "relative path outside" issue
                    dep_file = env.File(env['GCCDEP_FILENAME'](target, source, env, False))
                else:
                    dep_file = env.File(env.subst('$GCCDEP_FILENAME', 0, source, target))

                env.SideEffect(dep_file, target[0])

                script_dir = env.fs.getcwd()
                env.fs.chdir(env.Dir('#'))

                try:
                    # env.ParseDepends(dep_file.get_abspath())
                    env.XRefParseDepends(dep_file.get_abspath(), existing_only = True)
                finally:
                    env.fs.chdir(script_dir)

                env.Clean(target[0], dep_file)
            else:
                if has_makedep_flags:
                    if is_cc:
                        env['GCCDEP_MAKEDEP_CFLAGS'] = [ ]
                    else:
                        env['GCCDEP_MAKEDEP_CXXFLAGS'] = [ ]

    return target, source

def reload_dependency_file(target, source, env):
    getString   = base.BindCallArguments(base.getString, target, source, env, None)
    getList     = base.BindCallArguments(base.getList,   target, source, env, False)

    ext = os.path.splitext(str(source[0]))[1]
    is_cc  = ext in getList('GCCDEP_CSUFFIXES')
    is_cxx = ext in getList('GCCDEP_CXXSUFFIXES')

    if is_cc or is_cxx:
        is_static_obj = base.match_ixes(target[0], getString('GCCDEP_OBJPREFIX'),   getString('GCCDEP_OBJSUFFIX'))
        is_shared_obj = base.match_ixes(target[0], getString('GCCDEP_SHOBJPREFIX'), getString('GCCDEP_SHOBJSUFFIX'))

        if is_static_obj or is_shared_obj:
            if is_cc:
                if 'GCCDEP_MAKEDEP_CFLAGS' in env and env['GCCDEP_MAKEDEP_CFLAGS']:
                    env.XRefParseDepends(env.subst('$GCCDEP_FILENAME', 0, target, source))
            else:
                if 'GCCDEP_MAKEDEP_CXXFLAGS' in env and env['GCCDEP_MAKEDEP_CXXFLAGS']:
                    env.XRefParseDepends(env.subst('$GCCDEP_FILENAME', 0, target, source))

tool_basename_cache = { }

def find_tool_basename(env, cmd):
    path    = env['ENV']['PATH']    if 'ENV' in env and 'PATH'    in env['ENV'] else ''
    pathext = env['ENV']['PATHEXT'] if 'ENV' in env and 'PATHEXT' in env['ENV'] else ''

    if path not in tool_basename_cache:
        tool_basename_cache[path] = { }

    if pathext not in tool_basename_cache[path]:
        tool_basename_cache[path][pathext] = { }

    if cmd not in tool_basename_cache[path][pathext]:
        tool_basename_cache[path][pathext][cmd] = \
            os.path.splitext(os.path.split(os.path.realpath(env.WhereIs(cmd)))[1])[0]
        # print("Found tool " + str(env.WhereIs(cmd)) + " in path " + str(path))

    return tool_basename_cache[path][pathext][cmd]

def generate(env, **kw):
    """
        Populate the given environment with the information to run the tool
        Also inject the tool emitter for gcc dependency generation and parsing
        into existing Object / SharedObject builders in the environment
    """

    geBool  = base.BindCallArguments(base.getList, None, None, env, lambda x: x)
    getList = base.BindCallArguments(base.getList, None, None, env, False)

    env.SetDefault\
        (
            GCCDEP_SUFFIX   = '.d',
            GCCDEP_CSUFFIXES = [ '.c' ] + ([ ] if SCons.Util.case_sensitive_suffixes('.c', 'C') else [ '.C' ] ),
            GCCDEP_CXXSUFFIXES  =
                [ '.cc', '.cpp', '.cxx', '.c++', '.C++' ]
                    +
                ([ '.C' ] if SCons.Util.case_sensitive_suffixes('.c', '.C') else [ ]),
            GCCDEP_FILENAME =
                lambda target, source, env, for_signature:
                    env.File(target[0]).Dir('depend').Dir\
                        (
                            re.sub
                                (
                                    '((?<=^)|(?<=/))\.\.(?=(/|$))',
                                    '__',
                                    str(env.Dir('#').rel_path(source[0].srcnode().dir))
                                )
                        )
                            .File(str(target[0].name) + env.subst('$GCCDEP_SUFFIX', False, source, target)),
            GCCDEP_CFLAGS_VAR        = 'CFLAGS',
            GCCDEP_CXXFLAGS_VAR      = 'CXXFLAGS',
            GCCDEP_MAKEDEP_CFLAGS    = [ ],
            GCCDEP_MAKEDEP_CXXFLAGS  = [ ],
            GCCDEP_OBJPREFIX         = '$OBJPREFIX',
            GCCDEP_OBJSUFFIX         = '$OBJSUFFIX',
            GCCDEP_SHOBJPREFIX       = '$SHOBJPREFIX',
            GCCDEP_SHOBJSUFFIX       = '$SHOBJSUFFIX',
            GCCDEP_CFLAGS            = [ '-MD', '-MF', '$GCCDEP_FILENAME' ],
            GCCDEP_CXXFLAGS          = [ '-MD', '-MF', '$GCCDEP_FILENAME' ],
            GCCDEP_CC                = '$CC',
            GCCDEP_GCC_BASENAME      = 'gcc',
            GCCDEP_SHCC              = '$SHCC',
            GCCDEP_GCC_SH_BASENAME   = 'gcc',
            GCCDEP_CXX               = '$CXX',
            GCCDEP_GXX_BASENAME      = 'g++',
            GCCDEP_SHCXX             = '$SHCXX',
            GCCDEP_GXX_SH_BASENAME   = 'g++',
            GCCDEP_CHECK_USING_GCC   =
                lambda target, source, env, for_signature:
                    not not re.match
                        (
                            r'^(.*\b)?' + re.escape(env.subst('$GCCDEP_GCC_BASENAME', 1, source, target)) + r'(-[0-9\.]+)?(\b|\s|$)',
                            find_tool_basename(env, env.subst('$GCCDEP_CC', 0, source, target))
                        ),
            GCCDEP_CHECK_USING_SH_GCC   =
                lambda target, source, env, for_signature:
                    not not re.match
                        (
                            r'^(.*\b)?' + re.escape(env.subst('$GCCDEP_GCC_SH_BASENAME', 1, source, target)) + r'(-[0-9\.]+)?(\b|\s|$)',
                            find_tool_basename(env, env.subst('$GCCDEP_SHCC', 0, source, target))
                        ),
            GCCDEP_CHECK_USING_GXX   =
                lambda target, source, env, for_signature:
                    not not re.match
                        (
                            r'^(.*\b)?' + re.escape(env.subst('$GCCDEP_GXX_BASENAME', 1, source, target)) + r'(-[0-9\.]+)?(\b|\s|$)',
                            find_tool_basename(env, env.subst('$GCCDEP_CXX', 0, source, target))
                        ),
            GCCDEP_CHECK_USING_SH_GXX   =
                lambda target, source, env, for_signature:
                    not not re.match
                        (
                            r'^(.*\b)?' + re.escape(env.subst('$GCCDEP_GXX_SH_BASENAME', 1, source, target)) + r'(-[0-9\.]+)?(\b|\s|$)',
                            find_tool_basename(env, env.subst('$GCCDEP_SHCXX', 0, source, target))
                        ),
            GCCDEP_INJECTED = False
        )

    env.Append\
        (
            **
            {
                env['GCCDEP_CFLAGS_VAR']:   [ '$GCCDEP_MAKEDEP_CFLAGS' ],
                env['GCCDEP_CXXFLAGS_VAR']: [ '$GCCDEP_MAKEDEP_CXXFLAGS' ]
            }
        )

    builders = [ env['BUILDERS'][name] for name in [ 'StaticObject', 'SharedObject' ] if name in env['BUILDERS'] ]

    if 'Object' in env['BUILDERS']:
        objectBuilder = env['BUILDERS']['Object']
        if objectBuilder not in builders:
            builders.append(objectBuilder)

    # print("Selected builders: " + str(builders))

    for builder in builders:
        # inject gcc_dep_emitter in the current builder
        if isinstance(builder.emitter, DictEmitter):
            for ext in getList('GCCDEP_CSUFFIXES') + getList('GCCDEP_CXXSUFFIXES'):
                if ext in builder.emitter:
                    if isinstance(builder.emitter[ext], ListEmitter):
                        if gcc_dep_emitter not in builder.emitter[ext]:
                            builder.emitter[ext].append(gcc_dep_emitter)
                            # print('\033[92m' "Emitter injected in Builder list in dict" '\033[0m')
                    else:
                        builder.emitter[ext] = ListEmitter([ builder.emitter[ext], gcc_dep_emitter ])
                        # print('\033[92m' "Emitter injected in Builder dict in a new list" '\033[0m')
                else:
                    build.emitter[ext] = gcc_dep_emitter
                    # print('\033[92m' "Emitter injected in Builder dict" '\033[0m')
        else:
            if isinstance(builder.emitter, ListEmitter):
                if gcc_dep_emitter not in builder.emitter:
                    builder.emitter.append(gcc_dep_emitter)
                    # print('\033[92m' "Emitter injected in Builder list" '\033[0m')
            else:
                old_emitter = builder.emitter[ext]
                builder.emitter[ext] = ListEmitter([ old_emitter, gcc_dep_emitter ])

        if isinstance(builder, CompositeBuilder):
            for ext in getList('GCCDEP_CSUFFIXES') + getList('GCCDEP_CXXSUFFIXES'):
                try:
                    if ext in builder.cmdgen:
                        builder.add_action\
                                (
                                    ext,
                                    ListAction
                                        (
                                            [
                                                builder.cmdgen[ext],
                                                env.Action(reload_dependency_file, lambda target, source, env: None)
                                            ]
                                        )
                                )
                except AttributeError:
                    pass

        env['GCCDEP_INJECTED'] = True
        env.AddMethod(XRefParseDepends)

def exists(env):
    """ Returns True """
    return True

"""
    SCons tool to generate a JSON Compilation Database file, specified in:
        https://clang.llvm.org/docs/JSONCompilationDatabase.html

    The file is a listing with a compilation command line for each translation unit for a target

    Syntax:
        CompileCommands('compile_commands.json', [ target... ])
        CompileCommands([ target... ])

        CompilationDatabase('compile_commands.json', [ target... ])
        CompilationDatabase([ target... ])

    The [ target... ] list, which is a list of sources for this builder, contains other executables and
    libraries built in the same project. Source files for this binaries will be included in the
    generated compile commands. Only C and C++ sources are listed by default.

    CompilationDatabase() is an alias for CompileCommands()
"""

import os
import re

import SCons.Node
import SCons.Environment
import SCons.Script

import source_browse_base as base

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

def is_cc_source(node, cc_suffixes):
    """ check if not is a source node with name matching the convention for C and C++ source files """

    if not node.is_derived():
        return node.get_suffix() in cc_suffixes

def build_suffix_map(target, source, env):
    """
        fills two maps with names of variables to be expanded by file name extension (suffix), using
        the list in the construction environment.
    """
    getList   = base.BindCallArguments(base.getList, target, source, env, False)

    obj_suffix_map   = { k: v for suffix in getList('CCCOM_COMMANDVAR')   for (k, v) in suffix.items() }
    shobj_suffix_map = { k: v for suffix in getList('CCCOM_SHCOMMANDVAR') for (k, v) in suffix.items() }

    return [ obj_suffix_map, shobj_suffix_map ]

def get_build_command(obj_ixes, suffix_map, target, source, env):
    """
        retrieve approperiate variable to expand, based on source and target file name conventions
        (source file language, target object file type)
    """
    basename = os.path.split(target.get_path())[1]

    if basename.startswith(obj_ixes[2]) and target.get_suffix() == obj_ixes[3]:
        suffix_map = suffix_map[1]
    else:
        suffix_map = suffix_map[0]

    if source.get_suffix() in suffix_map:
        return suffix_map[source.get_suffix()]

    print("No command found for building " + str(target) + " from " + str(source))
    return None

def json_escape_string(string):
    """ escape a string for inclusion in the generated .json file """
    return '"' + string.replace('\\', '\\\\').replace('"', '\\"') + '"'

def clone_build_env(env, overrides = { }):
    if isinstance(env, SCons.Environment.OverrideEnvironment) and '__subject' in env.__dict__:
        nested_overrides = { }
        nested_overrides.update(env.__dict__['overrides'])
        nested_overrides.update(overrides)

        return clone_build_env(env.__dict__['__subject'], nested_overrides)

    new_env = env.Clone()
    new_env.Replace(**overrides)

    return new_env.Clone()

def write_compile_commands(target, source, env):
    """
        generator function to write the compilation database file (default 'compile_commands.json') for
        the given list of source binaries (executables, libraries)
    """
    getString = base.BindCallArguments(base.getString, target, source, env, None)
    getList   = base.BindCallArguments(base.getList,   target, source, env, False)
    getBool   = base.BindCallArguments(base.getBool,   target, source, env, lambda x: x)

    obj_ixes = \
        map(getString, [ 'CCCOM_OBJPREFIX',  'CCCOM_OBJSUFFIX', 'CCCOM_SHOBJPREFIX', 'CCCOM_SHOBJSUFFIX' ])

    cc_suffixes = \
        getList('CCCOM_SUFFIXES')

    source            = env.Flatten(source)
    suffix_map        = build_suffix_map(target, source, env)
    has_previous_unit = False
    keep_variant_dir  = getBool('CCCOM_KEEP_VARIANT_DIR')

    db_file = [ '[' ]

    for src in source:
        nodeWalker = SCons.Node.Walker(src)
        child = nodeWalker.get_next()

        while child:
            if is_object_file(child, obj_ixes):
                for child_src in child.sources:
                    if is_cc_source(child_src, cc_suffixes):
                        build_env = clone_build_env(child.get_build_env())

                        build_targets = [ child ] + child.alter_targets()[0]

                        if keep_variant_dir:
                            build_sources = child.sources
                        else:
                            build_sources = [ obj_src.srcnode() for obj_src in child.sources ]

                        append_flags = getList('CCCOM_APPEND_FLAGS')
                        filter_flags = getList('CCCOM_REMOVE_FLAGS')
                        abs_file_path = getBool('CCCOM_ABSOLUTE_FILE')

                        if not keep_variant_dir or append_flags or filter_flags or 'CCCOM_FILTER_FUNC' in env:
                            for filter_set in filter_flags:
                                for var_name in filter_set:
                                    if var_name in build_env:
                                        for val in env.Split(filter_set[var_name]):
                                            if val in build_env[var_name]:
                                                if val in build_env[var_name]:
                                                    if isinstance(build_env[var_name], str):
                                                        build_env[var_name] = re.sub(r'(^|\s+)' + re.escape(val) + r'(\s+|$)', ' ', build_env[var_name])
                                                    else:
                                                        while val in build_env[var_name]:
                                                            build_env[var_name].remove(val)

                            for flag_set in append_flags:
                                build_env.Append(**flag_set)

                            if 'CCCOM_FILTER_FUNC' in env:
                                build_env['CCCOM_FILTER_FUNC'] = env['CCCOM_FILTER_FUNC']
                                build_env['CCCOM_ENV'] = env
                                val = base.getBool(build_targets, build_sources, build_env, lambda x: x, 'CCCOM_FILTER_FUNC')
                                if not val:
                                    continue

                        if has_previous_unit:
                            db_file.append('    },')

                        has_previous_unit = True

                        db_file.extend\
                            ([
            '    {',
            '        "directory": ' + json_escape_string(build_env.fs.getcwd().get_abspath()) + ','
                            ])

                        if keep_variant_dir:
                            src_file = child_src
                        else:
                            src_file = child_src.srcnode()

                        if abs_file_path:
                            src_file = src_file.get_abspath()
                        else:
                            src_file = src_file.get_path()

                        db_file.extend\
                            ([
            '        "file":      ' + json_escape_string(src_file) + ',',
            '        "command":   '
                    +
                json_escape_string\
                    (
                        build_env.subst\
                        (
                            get_build_command(obj_ixes, suffix_map, child, child_src, build_env),
                            False,
                            build_targets,
                            build_sources,
                            None
                        )
                    ) + ',',
            '        "output":    '
                    +
                json_escape_string(env.subst('$TARGET', False, build_targets, build_sources))
                            ])
            child = nodeWalker.get_next()

    if has_previous_unit:
        db_file.append('    }')

    db_file.append(']')

    with open(str(target[0]), 'w') as output_file:
        for line in db_file:
            output_file.write(line + '\n')


CompileCommandsBuilder = SCons.Script.Builder\
            (
                action = SCons.Script.Action(write_compile_commands, "Writing $TARGET"),
                multi  = True,
                suffix = '.json'
            )

def JSONCompilationDatabase(env, *args, **kw):
    """
        pseudo-builder (environement method) to translate source and target arguments as needed for the
        CompileCommandsBuilder(), and call that with the right arguments.
    """

    getString = base.BindCallArguments(base.getString, None, None, env, None)

    if len(args) == 0:
        target, source = [ getString('CCCOM_DATABASE_FILE') ], [ '.' ]
    else:
        if len(args) == 1:
            target, source = [ getString('CCCOM_DATABASE_FILE') ], env.Flatten(args)
        else:
            target, source = env.Flatten(args[0]), env.Flatten(args[1:])

    return CompileCommandsBuilder(env, target, source, **kw)

def exists(env):
    """ Check if needed commands for generating comilation database file are present """
    return True

def generate(env, **kw):
    """ Populate construction variables in `env` environment needed for CompileCommands() builder:
            $CCCOM_OBJPREFIX, $CCCOM_OBJSUFFIX, $CCCOM_SHOBJPREFIX, $CCCOM_SHOBJSUFFIX,
            $CCCOM_SUFFIXES, $CCCOM_DATABASE_FILE

        Attaches CompileCommands() and CompilationDatabase() builders to the environment.
    """

    env.SetDefault\
        (
            CCCOM_OBJPREFIX        = '$OBJPREFIX',
            CCCOM_OBJSUFFIX        = '$OBJSUFFIX',
            CCCOM_SHOBJPREFIX      = '$SHOBJPREFIX',
            CCCOM_SHOBJSUFFIX      = '$SHOBJSUFFIX',
            CCCOM_SUFFIXES         = [ '.c', '.m', '.C', '.cc', '.cpp', '.cxx', '.c++', '.C++', '.mm' ],
            CCCOM_COMMANDVAR       = \
                    [
                        { '.c':   '$CCCOM'  }, { '.m':   '$CCCOM'  },
                        { '.C':   '$CXXCOM' }, { '.cc':  '$CXXCOM' }, { '.cpp': '$CXXCOM' },
                        { '.cxx': '$CXXCOM' }, { '.c++': '$CXXCOM' }, { '.C++': '$CXXCOM' },
                        { '.mm':  '$CXXCOM' }
                    ],
            CCCOM_SHCOMMANDVAR     = \
                    [
                        { '.c':   '$SHCCCOM'  }, { '.m':   '$SHCCCOM' },
                        { '.C':   '$SHCXXCOM' }, { '.cc':  '$SHCXXCOM' }, { '.cpp': '$SHCXXCOM' },
                        { '.cxx': '$SHCXXCOM' }, { '.c++': '$SHCXXCOM' }, { '.C++': '$SHCXXCOM' },
                        { '.mm':  '$SHCXXCOM' }
                    ],
            CCCOM_DATABASE_FILE    = 'compile_commands.json',
            CCCOM_KEEP_VARIANT_DIR = False,
            CCCOM_APPEND_FLAGS     = [ ],
            CCCOM_REMOVE_FLAGS     = [ ],
            # CCCOM_FILTER_FUNC      = lambda target, source, env, for_signature: True
            CCCOM_ABSOLUTE_FILE    = False
        )

    env.AddMethod(JSONCompilationDatabase, 'CompileCommands')
    env.AddMethod(JSONCompilationDatabase, 'CompilationDatabase')

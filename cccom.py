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

import SCons.Node
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
        (source file language, target object file type
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

def write_compile_commands(target, source, env):
    """
        generator function to write the compilation database file (default 'compile_commands.json') for
        the given list of source binaries (executables, libraries)
    """
    getString = base.BindCallArguments(base.getString, target, source, env, None)
    getList   = base.BindCallArguments(base.getList,   target, source, env, False)
    getBool   = base.BindCallArguments(base.getBool,   target, source, env, None)

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
                        build_env = child.get_build_env()

                        if not keep_variant_dir:
                            build_env = build_env.Clone()
                            build_env.fs.chdir(build_env.fs.getcwd().srcnode())

                        if has_previous_unit:
                            db_file.append('    },')

                        has_previous_unit = True

                        db_file.extend\
                            ([
            '    {',
            '        "directory": ' + json_escape_string(build_env.fs.getcwd().get_abspath()) + ',',
            '        "file":      ' + json_escape_string(child_src.srcnode().get_path()) + ',',
            '        "command":   '
                    +
                json_escape_string(build_env.subst\
                        (
                            get_build_command(obj_ixes, suffix_map, child, child_src, build_env),
                            False,
                            [ child ] + child.alter_targets()[0],
                            [ obj_src.srcnode() for obj_src in child.sources ],
                            None
                        ))
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
            CCCOM_KEEP_VARIANT_DIR = False
        )

    env.AddMethod(JSONCompilationDatabase, 'CompileCommands')
    env.AddMethod(JSONCompilationDatabase, 'CompilationDatabase')

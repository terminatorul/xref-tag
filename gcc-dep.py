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
import source_browse_base as base

from SCons.Builder import DictEmitter, CompositeBuilder
from SCons.Builder import ListEmitter
from SCons.Action  import ListAction

def gcc_dep_emitter(target, source, env):
    """
        emitter function for SCons Builders, injected into the existing Object / SharedObject
        builders in the environment, to include and load the new dependency file with the 
        object
    """
    getList     = base.BindCallArguments(base.getList,   target, source, env, False)
    getString   = base.BindCallArguments(base.getString, target, source, env, None)

    if len(target):
        ext = os.path.splitext(str(source[0]))[1]

        if ext in getList('GCCDEP_SUFFIXES'):
            env.SideEffect(str(target[0]) + getString('GCCDEP_SUFFIX'), target[0])
            env.ParseDepends(str(target[0]) + getString('GCCDEP_SUFFIX'))
            env.Clean(target[0], str(target[0]) + getString('GCCDEP_SUFFIX'))

    return target, source

def reload_dependency_file(target, source, env):
    env.ParseDepends(str(target[0]) + base.getString(target, source, env, False, 'GCCDEP_SUFFIX'))

def generate(env, **kw):
    """
        Populate the given environment with the information to run the tool
        Also inject the tool emitter for gcc dependency generation and parsing
        into existing Object / SharedObject builders in the environment
    """

    getList = base.BindCallArguments(base.getList, None, None, env, False)

    env.SetDefault\
        (
            GCCDEP_SUFFIX   = '.d',
            GCCDEP_SUFFIXES = [ '.c', '.cc', '.cpp', '.cxx', '.c++', '.C++', '.C' ],
            GCCDEP_FLAGS    = [ '-MD', '-MF', '${TARGET}${GCCDEP_SUFFIX}', '-MT', '${TARGET.abspath}' ],
            GCCDEP_INJECTED = False
        )
    env.Append(CCFLAGS = env['GCCDEP_FLAGS'])

    builders = [ env['BUILDERS'][name] for name in [ 'StaticObject', 'SharedObject' ] if name in env['BUILDERS'] ]

    if 'Object' in env['BUILDERS']:
        objectBuilder = env['BUILDERS']['Object']
        if objectBuilder not in builders:
            builders.append(objectBuilder)

    # print("Selected builders: " + str(builders))

    for builder in builders:
        # inject gcc_dep_emitter in the current builder
        if isinstance(builder.emitter, DictEmitter):
            for ext in getList('GCCDEP_SUFFIXES'):
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
            for ext in getList('GCCDEP_SUFFIXES'):
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

def exists(env):
    """ Return True if the tool is present in the environment """
    return env.get('GCCDEP_INJECTED', False)

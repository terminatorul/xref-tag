"""
    Automatically use gcc / g++ compilers to generate preprocessed and assembly sources
    during compilation

    These are regenerated every time the compiler is invoked for any source files in the
    environment.

    Requires 'gcc' or 'g++' tools in the current environment, as the options used are
    specific to the GNU compilers.
"""

import os
from SCons.Builder import DictEmitter
from SCons.Builder import ListEmitter

def gcc_cpp_emitter(target, source, env):
    """
        emitter function for SCons Builders, injected into the existing Object / SharedObject
        builders in the environment, to include and load the new dependency file with the
        object
    """
    if len(target):
        src_ext     = os.path.splitext(str(source[0]))[1]
        target_base = os.path.splitext(str(target[0]))[0]

        if src_ext in env['GCCCPP_SUFFIXES']:
            for suffix in env['GCCCPP_SUFFIX']:
                if suffix == '.ii' and src_ext == '.c':
                    suffix = '.i'

                env.SideEffect(target_base + suffix, target[0])
                env.Clean(target[0], target_base + suffix)

    return target, source

def generate(env, **kw):
    """
        Populate the given environment with the information to run the tool
        Also inject the tool emitter for gcc intermediate targets (cpp / as)
        into the existing Object builder / SharedObject builder in the
        environment
    """
    env.SetDefault\
        (
            GCCCPP_SUFFIX   = [ '.ii', '.s' ],
            GCCCPP_SUFFIXES = [ '.c', '.cc', '.cpp', '.cxx', '.c++', '.C++', '.C' ],
            GCCCPP_FLAGS    = [ '-save-temps=obj' ],
            GCCCPP_INJECTED = False
        )
    env.Append(CCFLAGS = env['GCCCPP_FLAGS'], CXXFLAGS = env['GCCCPP_FLAGS'])

    builders = [ env['BUILDERS'][name] for name in [ 'StaticObject', 'SharedObject' ] if name in env['BUILDERS'] ]

    objectBuilder = env['BUILDERS']['Object']
    if objectBuilder not in builders:
        builders.append(objectBuilder)

    # print("Selected builders: " + str(builders))

    for builder in builders:
        # inject gcc_cpp_emitter in the current builder
        if isinstance(builder.emitter, DictEmitter):
            for ext in env['GCCCPP_SUFFIXES']:
                if ext in builder.emitter:
                    if isinstance(builder.emitter[ext], ListEmitter):
                        if gcc_cpp_emitter not in builder.emitter[ext]:
                            builder.emitter[ext].append(gcc_cpp_emitter)
                            # print('\033[92m' "Emitter injected in Builder list in dict" '\033[0m')
                    else:
                        old_emitter = builder.emitter[ext]
                        builder.emitter[ext] = ListEmitter()
                        builder.emitter[ext].append(old_emitter)
                        builder.emitter[ext].append(gcc_cpp_emitter)
                        # print('\033[92m' "Emitter injected in Builder dict in a new list" '\033[0m')
                else:
                    build.emitter[ext] = gcc_cpp_emitter
                    # print('\033[92m' "Emitter injected in Builder dict" '\033[0m')
        else:
            if isinstance(builder.emitter, ListEmitter):
                if gcc_cpp_emitter not in builder.emitter:
                    builder.emitter.append(gcc_cpp_emitter)
                    # print('\033[92m' "Emitter injected in Builder list" '\033[0m')
            else:
                old_emitter = builder.emitter[ext]
                builder.emitter[ext] = ListEmitter([ old_emitter, gcc_cpp_emitter ])

        env['GCCCPP_INJECTED'] = True

def exists(env):
    """ Return True if the tool is present in the environment """
    return env['GCCCPP_INJECTED']


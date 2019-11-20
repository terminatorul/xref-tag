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
        Similar to the SCons environment ParseDepends() method, with the following additions:
            - filenames with spaces and tabs are properly parsed, as long as file names do not end with
              the escape character '\\', which can trigger errors.
            - a target filename with colons is properly parsed
            - provide option to only add dependencies that exist in the file system, so if user deletes
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
    getList     = base.BindCallArguments(base.getList,   target, source, env, False)
    getString   = base.BindCallArguments(base.getString, target, source, env, None)

    if len(target):
        ext = os.path.splitext(str(source[0]))[1]

        if ext in getList('GCCDEP_SUFFIXES'):

            if callable(env['GCCDEP_FILENAME']):
                # make explicit call to work around the relative path outside issue
                dep_file = env.File(env['GCCDEP_FILENAME'](target, source, env, False))
            else:
                dep_file = env.File(env.subst('$GCCDEP_FILENAME', False, source, target))

            env.SideEffect(dep_file, target[0])

            script_dir = env.fs.getcwd()
            env.fs.chdir(env.Dir('#'))

            try:
                # env.ParseDepends(dep_file.get_abspath())
                env.XRefParseDepends(dep_file.get_abspath(), existing_only = True)
            finally:
                env.fs.chdir(script_dir)

            env.Clean(target[0], dep_file)

    return target, source

def reload_dependency_file(target, source, env):
    env.XRefParseDepends(env.subst('$GCCDEP_FILENAME', False, target, source))

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
            GCCDEP_FLAGS    = [ '-MD', '-MF', '$GCCDEP_FILENAME' ],
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
        env.AddMethod(XRefParseDepends)

def exists(env):
    """ Return True if the tool is present in the environment """
    return env.get('GCCDEP_INJECTED', False)

# xref-tag

SConstruct Tools and Builders for generating tag and cross-reference files on Linux for C and C++.

A tag here is the file position where a symbol in the source code (a function, class, variable,
...) is defined. A cross-reference or reference list is the set of file positions where a symbol
is referenced (used), for example all locations where a given function is called.

## Installation

Clone the repository under your `site_scons/site_tools/` directory for your project:

    cd .../projects/<octo-succotash>/
    mkdir site_scons/site_tools/
    cd site_scons/site_tools/
    git clone https://github.com/terminatorul/xref-tag.git

The main SConstruct build script `sconstruct` or `SConstruct` should be on the same level in the
directory tree with `site_scons/`, see [SCons user manual](https://scons.org/doc/production/HTML/scons-user.html#sect-environment-toolpath).
Alternatively you can use any other directory for installation and pass it on the `toolpath`
argument in the scons script when you want to load one of the tools, see [Construction
Environments](https://scons.org/doc/production/HTML/scons-man.html#construction_environments) in
SCons manual.

## Usage
In the `SConscript` you can include the tools when you create a construction environment, like

```python
    env = Environment(tools = ['default', 'xref-tag.gcc-dep', 'xref-tag.ctags', 'xref-tag.cscope' ])
```

If the tools are not installed on the default tool path, specify the install directory with an
explicit `toolpath` argument:

```python
    env = Environment(tools = ['default', 'xref-tag.gtags'], toolpath = [ xref_tag_install_dir ])
```

After creating the environment with the `xref-tag` tools, you can use the SCons Builders that are
now available to create new targets in your build script that will run `ctags`, `cscope`, `gtags`
or `cflow` commands to build tag and cross-reference files for your source code:

```python
    lib = env.SharedLibrary('octo', [ lib-src-files... ])
    exe = env.Program('succotash', [ exe-src-files... ])

    ctags = env.TagsFile  ('tags',       [ lib, exe, other sources ... ])
    xref  = env.CScopexRef('cscope.out', [ lib, other sources ... ])
    flow  = env.CFlowTree (              [ exe, ... ])
    gtags = env.GTAGS     ('.',          [ lib, exe, src... ])

    tags  = env.Alias     ('all-tags',   [ ctags, xref, flow, gtags ]) # use if you like Aliases
```

## Included tools
- '**xref-tag.gtags**'

  Configures the build environment with the variables to run `gtags` command from GNU GLOBAL
  source code tagging system, available from https://www.gnu.org/software/global/ and from most
  Linux distributions.

  Ex. installation for Ubuntu Linux: `apt install global`

  By default GNU GLOBAL 6.6.3 is expected.

  GNU global this is the most recently developed of the code browsing commands supported. It only
  supports parsing files inside the current project directory. To allow indexing of any sources
  and `#include`s outside the project, this tool will run the `gtags` command by default in the
  root directory of the file system, but will use the proper options on the command line to
  keep the resulting files in the project directory. Searching for a tag with GNU global will
  still show results relative to the current directory. To change this behavior and see
  the other options, check Variables List bellow.

  Builder:
    - gtags = **GTAGS**('dbpath', [ targets... ])

      The `dbpath` is the directory where the tag and reference files `GTAGS`, `GRTAGS`, `GPATH`
      and `GTAGSROOT` will be generated. Optional, the default will be set to the local
      `SConscript` directory `Dir('.').srcnode()` at the time the environment is created.

      All source files used to build the given targets will be enumerated and passed to the
      `gtags` command, with all known dependency `#include`s. You can also pass source files
      directly instead of the targets, but scanning for nested `#include`s will be limited, as
      the file is never compiled, so this is not recommended.

      To guarantee that all dependency `#include`s are known, including system headers, add
      to the same build environment the '**xref-tag.gcc-dep**' tool, that will append `gcc` and
      `g++` options to always list `#include` dependencies when source files are compiled, see
      bellow. With this mechanism however you will need to run tag generation a second time
      after the first build, and after `#include` line changes in a source file, see [ParseDepends()](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual.

      After the tag and reference files are generated, you can use `global` or `gtags-cscope`
      commands to query for symbol definition or uses, or integrate with an editor (like gVim)
      or IDE for this purpose.

      If you use `gtags-cscope`, beware it will try to update the resulting tag and reference
      files automatically before use, but without the same options on the command line that
      SCons is using. This means you should have a `gtags.conf` or `~/.globalrc` file with the same
      configuration as provided by SCons, or else the C++ system headers for example with
      no extension (like `<iostream>`) will be considered plain text files, and no C++ symbol
      defintions or references will be visible. Or you can always use `-d` option on
      `gtags-cscope` command line, to disable the automatic update of the reference files.

- '**xref-tag.cscope**'

  Configures the build environment with variables to run `cscope` command, available from http://cscope.sourceforge.net/
  and from most Linux distributions.

    Ex. installation for Ubuntu `apt install cscope`

  By default cscope version 15.8b is expected.

  According to the documentation `cscope` command is meant to reference and navigate `C` source
  code, but it is known to still work with `C++` for most uses, so this tool will pass `C++` 
  source file to the command.

  Builders:
    - xref = **CScopeXRef**('xreffile', [ targets... ])

      The `xreffile` will be generated with `cscope` command, with references to symbols in the
      source files. Passing the `xreffile` is optional, if not given the default will be
      `cscope.out` in the local `SConscript` directory. An additional `namefile` will
      be created in the same directory named `cscope.files` by default, holding the same list of
      files that was used to generate the `xreffile`. This file is later used by `cscope` command to
      keep the `xreffile` up-to-date next time it is needed. But in order to properly detect
      changes in `#include` lines, it is recommended to always use SConstruct to build the
      `xreffile` target again, in order to update it. Two more files, `cscope.out.in` and
      `csope.out.po` are placed in the same directory, to hold an additional inverted
      index that will speed up symbol look-ups.

      All source dependencies for the given `targets...` will be enumerated and passed to the
      `cscope` command for building the cross-reference. You can also give source files as
      `targets...`, but scanning for nested `#include`s will be limited, as the file is not
      compiled, so doing so is not recommended.

      To guarantee that all dependency `#include`s are known, including system headers, add the
      '**xref-tag.gcc-dep**' tool (see bellow) to the same SCons build environment. This will append
      `gcc` and `g++` command options to always output the list of `#include` dependencies when
      source files are compiled. With this mechanism however you will need to run tag
      generation a second time after the first build and after any `#include` line changes in a
      source file, see [ParseDepends()](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual for this issue.

      After the cross-reference fils is generated, you can use `cscope` command in the same
      directory to find symbols from the source files and their uses in the given targets.
      `cscope` command will update the cross-reference file before usbefore use. But if you
      move things around in your project and change the include directories, `cscope` will not
      know about it untill your regenerate the `xreffile` with SCons. Some editors integrate with
      `cscope` to get access to the refrences for navigation while editing. If not, the `cscope`
      command works both in an interactive terminal with a Text User Interface (TUI), or in the
      good old command line mode with the `-L` and `-0` .. `-9` options.

      If you split your project in subprojects, each with its own `cscope.out` file in its directory,
      an editor like `Vim` will still be able to load them all. See [Vim support](#vim-support-function)
      for a Vim function plus key mapping for loading `cscope.out` and `cscope.lib.out` files under
      the current directory, which is recursively searched up to 4 levels deep by default.

- '**xref-tag.ctags**'

   Configures the build environment with variables to run `ctags` command, either one of:
    - exuberant-ctags: http://ctags.sourceforge.net/
    - universal-ctags: https://ctags.io/

   `ctags` is also available from most Linux distributions.

   Ex. installation for Ubuntu Linux: `apt install exuberant-ctags`

   By default Exuberant ctags 5.9 is expected.

   This command can only generate a tags file and locate symbol definitions, with no
   cross-references, so there is no option to search for all uses of a function or variable.

   However `catgs` can parse a large list of languages and is generally a more reliable tool
   at what it does, because parsing C++ code for references is complex and is normally not
   implemented properly in various tools.

   Another detail is that `ctags` implements no incremental update. Although scanning is fast
   anyway, so it is only a problem for large projects that already have larger build times.
   And it is possible to simulate an incremental update by properly manipulating the tags
   file before running `ctags`.

   Builder:
    - ctags = **TagsFile**('tags', [ target... ])

      `ctags` command will generate the given `tags` file with symbol definitions. The `tags`
      file is optional, the default will be `tags` file in the local `SConscript` source
      directory (at the time environment is created).

      All source dependencies for the given `targets...` will be enumerated and passed to
      `ctags` command for scanning and generating tags. You can also give source files as
      `targets...`, but scanning for nested `#include`s will be limited, as the file is not
      compiled, so doing so is not recommended.


      '**xref-tag.gcc-dep**' tool (see bellow) to the same SCons build environment. This will
      append `gcc` and `g++` command options to always output the list of `#include`
      dependencies when source files are compiled. With this mechanism however you will need
      to run tag generation a second time after the first build and after any `#include` line
      changes in a source file, see [ParseDepends()](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual for this issue.

      After the tags file is generated, it can be used in editors / IDEs that itegrate tag
      files for navigationn while editing. The file format is text-based and rather simple,
      so there are tools that can generate and use a tags file for many languages. There is no
      command line access to the tags in the file by default, but if you can search it, with
      Linux `grep` command for example, so to find the main function type: `grep ^main tags`.

- '**xref-tag.cflow**'

    Configures the build environment with variables for running `cflow` command, available at:
	- https://www.gnu.org/software/cflow/

    Ex. installation for Ubuntu Linux: `sudo apt install cflow`

    By default GNU cflow 1.6 is expected.

    The command works with 'C' sources (although I was able to parse some C++ with it, but not
    classes), and will output a direct and reverse call graph for the entire set of sources.
    Will also output a third format which is a cross-references of uses (calls) and definitions
    for functions, in line-oriented text format.

    Unfortunately unreliable in my experience, the command has options to parse pre-processed
    source for better visibility into the definitions and syntax, but I struggled to get it to
    work at all while developing the SConstruct integration, so now it works in no-preprocessing
    mode, which produces a detailed static listing of every function call, presented in a tree
    with indentation or with ASCII art.

    Builder:
     - cflow = **CFlowTree**('calltree.cflow', [ targets... ])

       Will output 3 files related to the call tree of the given target:
	    - a direct call tree, with the default extension `.cflow`
	    - a reverse call tree, with extension `.reverse.cflow`
	    - a listing referencing all function calls found, with extension `.xref.cflow` 


       All sources for the given `targets...` will be enumerated and passed to the `cflow` command
       line. You can also pass source files as the `targets...`, and they will be included in
       the `ctags` command line.

       It is still recommended to load the '**xref-tag.gcc-dep**' tool to guarantee the correct
       list of `#include` dependencies is found. With this mechanism however you will need to run
       tag generation a second time after the first build and after any `#include` line changes
       in a source file, see [ParseDepends()](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
       function in SCons user manual for this issue.

       After generating the call graph, it can be immediately inspected as it is a text file
       with proper indentation and possibly showing an ASCII tree if the options are included.

- '**xref-tag.gcc-dep**'

    Configures `gcc` and `g++` command line options in the given build environment for listing
    the complete list of `#include` file dependencies during compilation. This guarantees that
    no symbol will be missing from the generated tags, but also means that the additional dependency
    files are loaded every time `scons` runs. This takes some time and may become noticible on large
    (enterprise) projects.

    There are no Builders exposed by `'xref-tag.gcc-dep'`. It must be loaded _after_ `gcc` and `g++`,
    and will automatically inject:

	- options to generate a dependecy file (`*.d`) next to the object file at compile time:
	- loading previous generated dependency files whenever `scons` starts
	- loading re-generated dependency files again after a compilation
	- adding the dependency file to the build system so they are added to the targets to
	  be cleaned

- '**xref-tag.gcc-cpp**'

    Configures `gcc` and `g++` command line options in the given environement, for listing the
    preprocessed output and the assembly listing file during compilation, and keeping the files
    for later. This tool must be loaded *after* `gcc` and `g++` are loaded, and it will:
	- add `-save-temps=obj` option to `gcc` command line to save the preprocessed and assembly
	  files during compilation
	- automatically add the new files as side-effects of building the new object files, and
	  add them as dependencies to be cleaned when cleaning the object file target

    This module is not currently used and will waste a lot of disk space, however in general
    there is some value in the preprocessed source for the source code cross-reference commands,
    for example `ctags` has an option following `#line` directives in preprocessed sources.

## Tool variables:

 - '**xref-tag.gtags**'
    - `$GTAGS`
	    - `gtags` command name, default `gtags`
    - `$GTAGSDBPATH`
	    - default destination directory when only sources arg is  given to the builder call,
	      default `#/`
    - `$GTAGSFLAGS`
	    - other command line options to pass to `gtags` command, default `[ '--statistics' ]`
    - `$GTAGSSTDINFLAG`
	    - list of flags needed for nested `gtags` process to have the process read the list of
	      files from standard input, default `[ '-f', '-' ]`
    - `$GTAGSCONFIGFLAG`
	    - list of `gtags` command line flags for selecting a confguration file, default
		`[ '--gtagsconf' ]`
    - `$GTAGSOUTPUTFLAG`
	    - list of `gtags` command options for selecting the output files (`GTAGS`, `GRTAGS` and
	      `GPATH`). Default empty `[ ]`, as `gtags` has no such options.
    - `$GTAGSOUTPUTS`
	    - files that will be output by `gtags` after generating the tags in the `dbpath`
	       directory. Default `[ 'GTAGS', 'GRTAGS', 'GPATH' , 'GTAGSROOT' ]`, except the last
	       output file `GTAGSROOT` is generated by the `'xref-tag.gtags'` tool at buiild time
	       from the `$GITASROOT` variable, if seet
    - `$GTAGSROOT`
	    - common root directoy for all the files in the project, including system headers that
	      may be loaded by `xref-tag.gcc-dep` tool. Files outside this directory will be
	      ignored by `gtags` even if given as input for tag file generation. The value of this
	      variable is written at build time in the `GTAGSROOT` file in `dbpath`. Default is
	      the filesystem root `/`.
    - `$GTAGSADDENV`
	    - dictionary with environment variables to be passed to the `gtags` subprocess for 
	      tag generation. Default `{ 'GTAGSFORCECPP': 1 }` to allow parsing `.h` files as
	      `C++` instead of the default language `C`
    - `$GTAGSCONFIGLIST`
	    - list of config files, searched and loaded by `gtags` command by default. Only used
	      as additional dependencies to the resulting tag and reference files, as they should
	      be re-generated when the tool configuration changes for example the language map.

	      The option is only used when `$GTAGSCONFIG` is not given, as otherwise that value
	      takes precedence over the other config files.

	      Default `[ '/usr/local/etc/gtags.conf', '/etc/gtags.conf', os.path.join(os.environ['HOME'], '.globalrc'), '/gtags.conf' ]`
    - `$GTAGSCONFIG`
	    - `gtags` config file contents as a python list of lines of text. Written to a temporary file
	       at build time, with the temporary file name passed to `gtags` as the config file.
	       Default is:

		```python
                [
                    'default:\\',
                    '   :langmap=c\\:.c.h,yacc\\:.y,asm\\:.s.S,java\\:.java,cpp\\:.c++.cc.hh.cpp.cxx.hxx.hpp.C.H.tcc,php\\:.php.php3.phtml,cpp\\:(*):'
                ]
		```
		which is the `gtags` default language map, modified to allow parsing files without
		extension, like `<iostream>`, and files with `.tcc` extension, as `C++` sources
    - `$GTAGSSUFFIXES`
	    - a python list of suffixes for files that can be parsed by `gtags` command. Any files
	      with a non-matching extension will not be included as input to the `gtags` command.
	      Default is:

	      ```python
                [
                    '.c', '.h',
                    '.y',
                    '.s', '.S',
                    '.java',
                    '.c++', '.cc', '.hh', '.cpp', '.cxx', '.hxx', '.hpp', '.C', '.H', '.tcc', '',
                    '.php', '.php3', '.phtml'
                ]
	      ```
	      Extensions `.tcc` and `` above were added to the `gtags` default list of file
	      extensions, to support parsing system header files for GNU compiler.
 - '**xref-tag.cscope**'
    - `$CSCOPE`
	    - `cscope` command name, default `cscope`
    - `$CSCOPEQUICKFLAG`
	    - list of `cscope` flags to build a second inverted index for fast symbol look-ups.
	      The options is included in the default value for `$CSCOPEFLAGS`, and when
	      detected there will add the second index files as additional targets output from
	      the builder for `cscope` command. Default `[ '-q' ]`
    - `$CSCOPEFLAGS`
	    - list of command line flags to be passed to `cscope` command. Default
	      `[ '-b', '-q', '-k' ]` (build cross-reference, build quick-index and ignore system
	      (default) include directories)
    - `$CSCOPEINCFLAG`
	    - list of flags for passing an include directory to `cscope` command line, default
	      `[ '-I' ]`
    - `$CSCOPEPATH`
	    - list of include directories passed to `cscope` command. Each one will be preceded
	      on the resulting command line by the value of `$CSCOPEINCFLAG`. Default `$CPPPATH`.
    - `$CSCOPESYSPATH`
	    - list of system include directories, that are not normally listed on the compiler
	      command line or in `$CPPPATH`. Normally used together with the `-k` option to
	      disable automatic searching of the system include directories by `cscope`. To find
	      system include directories for GNU compilers, preprocess an empty source file with
	      the `-v` preprocessor flag. You can use `/dev/null` file and explicitly
	      specify the source language as `c` or `c++` with the `-x` option, like this:
	      ```
                 gcc -E -Wp,-v -xc   /dev/null
                 g++ -E -Wp,-v -xc++ /dev/null
	      ```
    - `$CSCOPEDIRECTORY`
	    - the directory to run `cscope` in. This is significant for the resulting
	      cross-reference file and should be the directory that you will be using `cscope`
	      from, for example the current directory in the source editor used for
	      code browsing. Default is the current source directory, given as
	      `env.Dir('.').srcnode()`. The given directory name, if not an absolute path,
	      will be relative to the local directory (current `SConscript` directory)
    - `$CSCOPESTDINFLAGS`
	    - list of `cscope` flags to request reading list of input files from standard input.
	      Used at build time to feed the running `cscope` process the list of input files,
	      one per line. Files with spaces are included in double quotes, and existing 
	      double quotes and back slashes in the file name are escaped with a backslash
    - `$CSCOPEOUTPUTFLAG`
	    - list fo `cscope` flags to give the main cross-reference file name. The inverted
	      index files are named after this file with the .in and .out extensions added
    - `$CSCOPEOUTPUTFILE`
	    - default name for the cross-reference file, used when the builder is called with
	      only the source nodes and not target node name
    - `$CSCOPENAMEFILE`
	    - default name for the `cscope` 'namefile'. The same list of input files given
	      to the `cscope` process for input is also written in this file during build, for
	      use be `cscope` at a later time to keep the xref file up-to-date. This file will
	      include the options present both on the command line and in `$CSCOPENAMEFILEFLAGS`
	      bellow, and all the include directories from command line if in case the same
	      variable allows the `$CSCOPEINCFLAGS` option.
    - `$CSCOPENAMEFILEFLAGS`
	    - list of flags from the command line that should be saved at the beginging of the
	      generated namefile. Default `[ '-I', '-c', '-k', '-p', '-q', '-T' ]`.
    - `$CSCOPESUFFIXES`
	    - python list of files suffixes that can be parsed by `cscope`. Non-matching source
	      files are filtered out and are not source nodes for the target xref file.
	      Default C and C++:
	      ``` python
                [
                    '',
                    '.c', '.y',
                    '.i', '.c++', '.cc', '.cp', '.cpp', '.cxx',
                    '.h', '.h++', '.hh', '.hp', '.hpp', '.hxx', '.C', '.H', '.tcc'
                ]
	      ```

- '**xref-tag.ctags**'
    - `$CTAGS`
	    - `ctags` command name, default `ctags`
    - `$CTAGSFLAGS`
	    - list command line flags to be passed to `ctags`. Default value:

             ```python
                [
                    '-h', '+.',
                    '--c-kinds=+px',
                    '--c++-kinds=+px',
                    '--extra=+q',
                    '--langmap=c++:+.tcc.',
                    '--fields=+iaSt',
                    '--totals=yes'
                ]
             ```

	     allows for a richer resulting tags file and for parsing files without an extension, like
	     `<iostream>`, plus files with `.tcc` extension, as `C++`
    - `$CTAGSDEFPREFIX`
	    - list of options to introduce a definition on `ctags` command line (similar to the compiler
	      definitions). Default `[ '-I' ]`
    - `$CTAGSSTDINFLAGS`
	    - list of `ctags` options for reading list of input files from the standard input stream
	      of the process. Default `[ '-L', '-' ]`
    - `$CTAGSOUTPUTFLAG`
	    - list of `ctags` flags to give the output file name (tags file name). Default `[ '-o' ]`
    - `$CTAGSDEF`
	    - list of macro definitions to be passed to `ctags` command line. Each of them will be
	      preceeded on the command line by the flags in `$CTAGSDEFPREFIX`. Default value includes
	      some macro replacements to allow `ctags` to parse system headers for GNU compiler:

	      ```python
                [
                    '_GLIBCXX_NOEXCEPT',
                    '_GLIBCXX_VISIBILITY+',
                    '_GLIBCXX_VISIBILITY(x)'
                ]
	      ```
    - `$CTAGSFILE`
	    - default name for the output file where tags are generated (the tags file). Used when the
	      builder is invoked with the source argument only, and no target argument. Default is the `#tags`
	      file in the top level SConstruct source directory
    - `$CTAGSCONFIG`
	    - python list of config files searched and loaded by default by `$CTAGS`. Only used as
	      additional dependencies for the resulting tags file, so tags will be regenerated when
	      `ctags` configuration changes. Default value:

	      ```python
                [
                    '/etc/ctags.conf',
                    '/usr/local/etc/ctags.conf',
                    os.path.join(os.environ['HOME'], '.ctags'),
                    '#.ctags'
                ]
	      ```
    - `$CTAGSSUFFIXES`
	    - python list of suffixes of files that `ctags` can parse and understand. Only matching
	      files will the given to `ctags` command, others are discarded. Default:

	      ```python
	      [
                    '',
                    '.build.xml',
                    '.asm', '.ASM', '.s', '.S', '.A51', '.29k', '.29K', # *.[68][68][kKsSxX] *.[xX][68][68]
                    '.asp', '.asa',
                    '.awk', '.gawk', '.mawk',
                    '.bas', '.bi', '.bb', '.pb',
                    '.bet',
                    '.c',
                    '.c++', '.cc', '.cp', '.cpp', '.cxx',
                    '.h', '.h++', '.hh', '.hp', '.hpp', '.hxx', '.C', '.H', '.tcc',
                    '.cs',
                    '.cbl', '.cob', '.CBL', '.COB',
                    '.bat', '.cmd',
                    '.e',
                    '.erl', '.ERL', '.hrl', '.HRL',
                    '.as', '.mxml',
                    '.f', '.for', '.ftn', '.f77', '.f90', '.f95',
                    '.F', '.FOR', '.FTN', '.F77', '.F90', '.F95',
                    '.go',
                    '.htm', '.html',
                    '.java',
                    '.js',
                    '.cl', '.clisp', '.el', '.l', '.lisp', '.lsp',
                    '.lua',
                    '.mak', '.mk', # [Mm]akefile GNUmakefile',
                    '.m',
                    '.m', '.h',
                    '.ml', '.mli',
                    '.p', '.pas',
                    '.pl', '.pm', '.plx', '.perl',
                    '.php', '.php3', '.phtml',
                    '.py', '.pyx', '.pxd', '.pxi', '.scons',
                    '.cmd', '.rexx', '.rx',
                    '.rb', '.ruby',
                    '.SCM', '.SM', '.sch', '.scheme', '.scm', '.sm',
                    '.sh', '.SH', '.bsh', '.bash', '.ksh', '.zsh',
                    '.sl',
                    '.sml', '.sig',
                    '.sql',
                    '.tcl', '.tk', '.wish', '.itcl',
                    '.tex',
                    '.vr', '.vri', '.vrh',
                    '.v',
                    '.vhdl', '.vhd',
                    '.vim',
                    '.y'
              ]
	      ```
- '**xref-tag.cflow**'
    - `$CFLOW`
	    - `cflow` command name, default `cflow`
    - `$CFLOWOUTPUTFLAG`
	    - list of `cflow` options for passing the output file name, default `[ '--output' ]`
    - `$CFLOWFLAGS`
	    - list of other flags to the `cflow` command, default `[ '--all', '--omit-symbol-name' ]`
    - `$CFLOWCONFIG`
	    - list of configuration files searched and loaded by `cflow` command. Only used as 
	      additional dependencies for the result call graph files, so the are regenerated when
	      `cflow` configuration changes. Default `[ os.path.join(os.environ['HOME'], `.cflowrc') ]`
    - `$CFLOWPATHFLAG`
	    - list of `cflow` options for passing an include directory, to be used for pre-processing
	      Default `[ '-I' ]`
    - `$CFLOWPATH`
	    - list of include directories to be passed to `cflow` for pre-processing. Each of them
	      will be preceeded on the command line by the options from `$CFLOWPATHFLAG`. Default
	      empty.
    - `$CFLOWDEFFLAG`
	    - `cflow` options for giving a macro definitions, to be used for pre-processing.
	      Default `[ '-D' ]`
    - `$CFLOWDEF`
	    - list of macro definitions given to `cflow` command for pre-processing. Each of them
	      will be preceeded by the options in `$CFLOWDEFFLAG`. Default empty
    - `$CFLOWFORMAT`
	    - python map form a nested file extension string to a cflow output format flag.
	      `cflow` command will be run once for each extension string found, with the associated
	      output format options. Default:

	      ```python
                 {
                    '':         [ ],
                    '.reverse': [ '--reverse' ],
                    '.xref':    [ '--xref' ]
                 }
	      ```
	      The `.cflow` file extension is appended by default after the nested extensions given
	      here.
    - `$CFLOWSYMFLAG`
	    - `cflow` options for giving a symbol on the command line, default `[ '--symbol' ]`
    - `$CFLOWSYM`
	    - list of symbols (name=type) to be given to `cflow` command to fix input files parsgin
	      Default value:

	      ```python
                [
                    '__inline:=inline',
                    '__inline__:=inline',
                    '__gnu_inline__:=inline',
                    '__always_inline__:=inline',
                    '__const__:=const',
                    '__const:=const',
                    '__restrict:=',
                    '__extension__:qualifier',
                    '__attribute__:wrapper',
                    '__asm__:wrapper',
                    '__nonnull:wrapper',
                    '__nonnull__:wrapper',
                    '__wur:wrapper',
                    '__nonnull__:wrapper',
                    '__artificial__:qualifier',
                    '__leaf__:qualifier',
                    '__nothrow__:qualifier',
                    '__artificial__:qualifier',
                    '__pure__:qualifier',
                    '__asm__:qualifier'
                ]
	      ```
    - `$CFLOWCPP`
	    - list of `cflow` options to request pre-processing input file before parsing and generating
	      the call graph. Currently `cflow` command is likely to break when parsing pre-processed
	      system header files, so doing so is not recommended. Default empty `[ ]`
    - `$CFLOWSUFFIXES`
	    - list of suffixes for files that `cflow` can parse and understand. Only matching source files
	      are given as input to the command. Default 'C' and 'C++':
	      ```python
                 [
                     '.c', '.y',
                     '','.c++', '.cc', '.cp', '.cpp', '.cxx', '.h', '.h++', '.hh', '.hp', '.hpp', '.hxx', '.C', '.H'
                 ]
	      ```

- '**xref-tag.gcc-dep**'

    - `$GCCDEP_FLAGS`
	    - list of `gcc` and `g++` flags to generate make dependency rule files for `#include`d files,
	      during compilation. Default `[  ]`
	      ```python
                 [
                     '-MD',
                     '-MF', '${TARGET}${GCCDEP_SUFFIX}',
                     '-MT', '${TARGET.srcdir}/${TARGET.name}'
                 ]
	      ```

    - `$GCCDEP_SUFFIX`
	    - suffix for the generated make dependency rules files, default `'.d'`

    - `$gccDEP_SUFFIXES`
	    - list of file suffixes for which the compiler can generate make dependency rules.
	      Default: `[ '.c', '.cc', '.cpp', '.cxx', '.c++', '.C++', '.C' ]`

    - `$GCCDEP_INJECTED`
	    - set to `True` when the tools was imported in the environment. Used to check if this tool
	      is already available in a given environment

- '**xref-tag.gcc-cpp**'

    - `$GCCCPP_FLAGS`
	    - list of `gcc` and `g++` flags to generate and keep pre-processed source during compilation

    - `$GCCCPP_SUFIX`
	    - list of suffixes of files output by the compiler with the proper command line options for
	      saving preprocessed source code to file. Default `[ '.ii', '.s' ]` The `.i` option is added
	      automaticall for '.c' files

    - `$GCCCPP_SUFFIXES`
	    - list of file suffixes that can be pre-processed by the compiler, so the pre-processed output
	      can be expected from the compiler, with the proper options. Default:
	      `[ '.c', '.cc', '.cpp', '.cxx', '.c++', '.C++', '.C' ]`

    - `$GCCCPP_INJECTED`
	    - set to `True` when the tool is imported in the environment. Can be later used to check if this
	      tool is already available in a given environment.

## Vim support function

If you have multiple sub-projects, each with their own cross-reference file `cscope.out`
(and `cscope.lib.out`), you can use the bellow function with the `Vim` editor to load them all for source
browsing while editing:

```vim
function g:LoadCScopeFiles(...)
    if a:0 > 1
	let l:depth_levels = a:1
	let l:path = a:2
	let l:cscope_file = a:3
	let l:subdir_list = [ ]

	if !l:depth_levels
	    return
	endif

	for l:entry in globpath(l:path, '*', v:true, v:true)
	    if isdirectory(l:entry)
		let l:entry = substitute(substitute(l:entry, '\', '\\', '\V'), ',', '\,', '\V')
		let l:subdir_list = add(l:subdir_list, l:entry)
	    else
		let l:basename = fnamemodify(l:entry, ':t')
		if l:basename == l:cscope_file
		    echomsg "Found cscope file: " . l:basename . " in directory " . fnamemodify(l:entry, ':h')
		    let l:location = fnamemodify(l:entry, ':h')

		    if l:location == '.'
			execute 'cscope add ' . fnameescape(l:entry)
		    else
			execute 'cscope add ' . fnameescape(l:entry) . ' ' . fnameescape(fnamemodify(l:entry, ':h'))
		    endif
		endif
	    endif
	endfor

	if len(l:subdir_list)
	    call LoadCScopeFiles(l:depth_levels - 1, join(l:subdir_list, ','), l:cscope_file)
	endif
    else
	if a:0
	    let l:depth_levels = a:1
	else
	    let l:depth_levels = 4
	endif

	call LoadCScopeFiles(l:depth_levels, '.', 'cscope.out')
	call LoadCScopeFiles(l:depth_levels, '.', 'cscope.lib.out')

	if filereadable('../cscope.out')
	    cscope add ../cscope.out ../
	endif

	if filereadable('../cscope.lib.out')
	    cscope add ../cscope.lib.out ../
	endif

	redrawstatus
	cscope show
    endif
endfunction

command LoadCScopeFiles call g:LoadCScopeFiles()
map <S-F5> :LoadCScopeFiles<CR>
```

Copy the function above in your `~/.vimrc` file (create one if it does not exist), change the last line
if you want a different key shortcut then `Shift + F5`, and then use this key combination when your
project is open, to have all the cross-reference files loaded. If you re-generate cross-reference files
using `scons`, while the editor is still using them, remember to type `:cscope reset` in `Vim` to
re-load them.

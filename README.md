# xref-tag

SConstruct Tools and Builders for generating tag and cross-reference files on Linux for C and C++.

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

    ctags = env.TagsFile  ('#tags',       [ lib, exe, other sources ... ])
    xref  = env.CScopexRef('#cscope.out', [ lib, other sources ... ])
    flow  = env.CFlowTree (               [ exe, ... ])
    gtags = env.GTAGS     ('#./',         [ lib, exe, src... ])

    tags  = env.Alias     ('tags',        [ ctags, xref, flow, gtags ]) # use if you like Aliases
```

## Included tools
- '**xref-tag.gtags**'

  Configures the build environment with the variables to run `gtags` command from GNU GLOBAL
  source code tagging system, available from https://www.gnu.org/software/global/.

  Ex. installation for Ubuntu Linux: `apt install global`

  GNU global this is the most recently developed of the code browsing tools supported. It only
  supports parsing files inside the current project directory. To allow indexing of any sources
  and `#include`s outside the project, this tool will run the `gtags` command by default in the
  root directory of the file system, but will use the proper options on the command line to
  keep the resulting files in the project directory. Searching for a tag with GNU global will
  still return located files relative to the current directory. To change this behavior and see
  the other options, check Variables List bellow.

  Builder:
    - gtags = **GTAGS**('dbpath', [ targets... ])

      The `dbpath` is the directory where the tag and reference files `GTAGS`, `GRTAGS`, `GPATH`
      and `GTAGSROOT` will be generated. Optional, the default will be set to the top-level
      `SConstruct` directory `#/`

      All source files used to build the given targets will be enumerated and passed to the
      `gtags` command, with all known dependency `#include`s. You can also pass source files
      directly instead of the targets, but scanning for nested `#include`s will be limited, as
      the file is never compiled, so this is not recommended.

      To guarantee that all dependency `#include`s are known, including system headers, add
      to the same build environment the '**xref-tag.gcc-dep**' tool, that will append `gcc` and
      `g++` options to always list `#include` dependencies when source files are compiled, see
      bellow. With this mechanism however you will need to run tag generation a second time
      after the first build and after any `#include` line changes in a source file, see [ParseDepends](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual.

      After the tag and reference files are generated, you can use `global` command to query for
      symbol definition or uses, or integrate with an editor (like gVim) or IDE for this purpose.

- '**xref-tag.cscope**'

  Configures the build environment with variables to run `cscope` command, available from http://cscope.sourceforge.net/'
  and from most Linux distributions.

    Ex. installation for Ubuntu `apt install cscope`

  According to the documentation `cscope` command is meant to reference and navigate `C` source
  code, but it is known to still work with `C++` for most uses, so this tool will pass `C++` 
  source file to the command.

  Builders:
    - xref = **CScopeXRef**('xreffile', [ targets... ])

      The `xreffile` will be generated with `cscope` command, with references to symbols in the
      source files. Passing the `xreffile` is optional, if not given the default will be
      `#cscope.out` in the top level SConstruct source directory. An additional `namefile` will
      be created in the same directory named `cscope.files` by default, holding the same list of
      files that was used to generate the `xreffile`. This file is used by `cscope` command to
      keep the `xreffile` up-to-date next time it is needed. But in order to properly detect
      changes in `#include` lines, it is recommended to always use SConstruct to build the
      `xreffile` target again, in order to update it. Two more files, `cscope.out.in` and
      `csope.out.po` are placed by default in the same directory, to hold an additional inverted
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
      source file, see [ParseDepends](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual for this issue.

      After the cross-reference fils is generated, you can use `cscope` command in the same
      directory to find symbols from the source files and their uses in the given targets.
      `cscope` command will also try to maintain an up-to-date cross-reference file while it is
      used, but keep in mind that `cscope` will not have your list of include directories and
      macro definitions from the project, but SConst does. Some editors can integrate with
      `cscope` and get access to the refrences for navigation while editing.

- '**xref-tag.ctags**'

   Configures the build environment with variables to run `ctags` command, either one of:
    - exuberant-ctags: http://ctags.sourceforge.net/
    - universal-ctags: https://ctags.io/

   Ex. installation for Ubuntu Linux: `apt install exuberant-ctags`

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
      file is optional, the default will be `#tags` file in the top-level SConstruct source
      directory

      All source dependencies for the given `targets...` will be enumerated and passed to
      `ctags` command for scanning and generating tags. You can also give source files as
      `targets...`, but scanning for nested `#include`s will be limited, as the file is not
      compiled, so doing so is not recommended.

      To guarantee that all dependency `#include`s are known, including system headers, add the
      `**xref-tag.gcc-dep**` tool (see bellow) to the same SCons build environment. This will
      append `gcc` and `g++` command options to always output the list of `#include`
      dependencies when source files are compiled. With this mechanism however you will need
      to run tag generation a second time after the first build and after any `#include` line
      changes in a source file, see [ParseDepends](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual for this issue.

      After the tags file is generated, it can be used in editors / IDEs that itegrate tag
      files for navigationn while editing. The file format is text-based and rather simple,
      so there are tools that can generate and use a tags file for many languages.

- '**xref-tag.cflow**'

    Configures the build environment with variables for running `cflow` command, available at:
	- https://www.gnu.org/software/cflow/

    Ex. installation for Ubuntu Linux: `sudo apt install cflow`

    The command works with 'C' sources (although I was able to parse some C++ with it, but not
    classes), and will output a direct and reverse call graph for the entire set of sources.
    Will also output a third format which is a cross-references of uses (calls) and definitions
    for functions, in line-oriented text format.

    Unfortunately unreliable in my experience, the command has an options to parse pre-processed
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
      in a source file, see [ParseDepends](https://scons.org/doc/production/HTML/scons-user.html#idm1236)
      function in SCons user manual for this issue.

      After generating the call graph, it can be immediately inspected as it is a text file
      with proper indentation and possibly and ASCII tree if the options are included.

- '**xref-tag.gcc-dep**'

    Configures `gcc` and `g++` command line options in the given build environment for listing
    the complete list of `#include` file dependencies during compilation. This guarantees that
    no symbol will be missing from the generated tags, but all the dependencies are immediately
    loaded every time `scons` runs. This takes a significant amout of time and will be no longer
    possible on large (enterprise) projects

    There are Builders exposed by `'xref-tag.gcc-dep'`. It must be loaded _after_ `gcc` and `g++`,
    and will automatically inject:

	- options to generate a dependecy file (.d) next to the object file at compile time
	- loading all generated dependency files whenever `scons` runs
	- adding the dependency file to the build system so they are added to the targets to
	  be cleaned

'**xref-tag.gcc-cpp**'

    Configrues `gcc` and `g++` command line options in the give environement for listing the
    preprocessed output and the assembly listing file during compilation, and keeping the files
    for later. In short. The tool must be loaded after 'gcc' and 'g++' are loaded, and it will:
	- add '-save-temps=obj' option to `gcc` command line to save the preprocessed and assembly
	  files during compilation
	- automatically add the new files as side-effects of building the new object files, and
	  add them as dependencies to be cleaned when cleaning the object file target

    This module is not currently used and will waste a lot of disk space, however in general
    there is some value in the preprocessed source for the source code cross-reference system
    so maybe it will be usefull later.

## Tool variables:

 - '**xref-tag.gtags**'
    - `şGTAGS`
	    - path to `gtags` command
    - `$GTAGSDBPATH`
	    - default destination directory when only sources are given to the builder
    - `$GTAGSFLAGS`
	    - other command line options to pass to `gtags` command
    - `$GTAGSSTDINFLAG`
	    - list of flags needed for nested `gtags` process to have the process read int input from
	    the konole (standard input)
	     it to read 

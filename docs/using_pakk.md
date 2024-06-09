<!-- MD+:META
title = "How to use pakk"
 -->




## Install Pakkages

```bash
pakk install PAKKAGE
```

Install a PAKKAGE (or multiple PAKKAGES).
You can specify a version with PAKKAGE@VERSION.
 If no version is specified, the latest version will be installed.

Options:
- `-F`, --force-reinstall: Reinstall defined pakkage even if it is already installed and up-to-date.
- `--refetch`: Refetches the pakkage from the server, otherwise already fetched pakkages are reused. Use in combination with `--force-reinstall` to reinstall a clean fetched copy of the package.
- `-U`, --upgrade: Upgrade all specified packages to the newest available version.
- `--clear-cache`: Clear the complete cache before installing. Use if you don't find versions that should be actually available.
- `--dry-run`: Don't actually install anything, just print what would be.
- `--no-deps`: Don't install pakkage dependencies.


## List

```bash
pakk ls -a ros2 # List all available ros2 pakkages, also non installed ones
```

List all installed pakkages. You can optionally specify a REGEX_FILTER expression to filter the list.

Options:
- -a, --all: Show all available pakkages.
- -x, --extended: Show extended information.
- -t, --types: Show the install types of the pakkage.

## Execution of Pakkages

### Run
```bash
pakk run PAKKAGE
```
Runs the given pakkage interactively.

### Start
```bash
pakk start PAKKAGE
```
Starts the given pakkages as services.

### Enable
```bash
pakk enable PAKKAGE
```
Enables the given pakkages.

### Stop
```bash
pakk stop PAKKAGE
```

Stops the given pakkage services.

### Disable
```bash
pakk disable PAKKAGE
```

Disables the given pakkages.


### Restart
```bash
pakk restart PAKKAGE
```

Restarts the given pakkages.

Options:
- `-r`, `--running`: Only restart running pakkages.
- `-e`, `--enabled`: Only restart enabled pakkages.

### Log
```bash
pakk log PAKKAGE
```
Follows the log of the given executable pakkage.

### Status

```bash
pakk status
```

Shows the status of startable pakkages in the system.


### Source

```bash
$(pakk source)
```

Sources the environment with all settings from the installed pakkages.
Installed pakkages can come with environment variables, which are sourced with this command to be used in manual testing.
These environment variables are necessary for the correct execution of other pakkages.

Just execute `pakk source` to see the environment variables that are set by pakk. `$()` is used to execute the output in the current shell.


## Other commands

### Tree
```bash
pakk tree
```

Show the dependency tree of a pakkage.

Options:
- -d, --depth: Maximum depth of the tree. 0 prints the complete tree.


### Init

```bash
pakk init PATH
```

Initialize a pakkage in the given path.

### Ros2
Run a ROS node from a package. Just type `pakk ros2` to see all available packages and nodes with auto completion.

```
$ pakk ros2
> ros2 run respeaker reSpeaker
```
